from fastapi import FastAPI, Request, Depends, HTTPException, status, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import uvicorn
import json
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
import re
import uuid
import os
import aiohttp
import asyncio
import logging
import sys

from .schemas import User, UserCreate, Token
from .auth import get_password_hash, verify_password, create_access_token, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
from .database import engine, get_db, SessionLocal
from .models import SerialNumber, Report, User as UserModel, DatabaseBase

# 创建数据库表
DatabaseBase.metadata.create_all(bind=engine)

app = FastAPI()

# 配置CORS - 支持Vercel部署
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",  # 允许所有来源（仅用于测试）
        "http://localhost:5173",  # 前端开发服务器地址
        "http://localhost:3000",  # 前端开发服务器地址（备用端口）
        "https://*.vercel.app",   # Vercel部署的域名
        "https://*.now.sh",       # Vercel旧域名
        "https://article-front-66q1-mo4kaklq9-cqhs-projects-63c79c7e.vercel.app",  # 你的前端域名
        "https://article-front-66q1.vercel.app",  # 前端主域名
        "https://article-front-66q1-*.vercel.app",  # 前端预览域名
        os.environ.get("FRONTEND_URL", "https://your-frontend-domain.vercel.app")  # 环境变量配置的前端URL
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

@app.get("/")
def read_root():
    return {"Hello": "World"}

# 用户注册
@app.post("/api/register", response_model=User)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    # 检查邮箱是否已存在
    db_user = db.query(UserModel).filter(UserModel.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # 创建新用户
    hashed_password = get_password_hash(user.password)
    db_user = UserModel(
        email=user.email,
        hashed_password=hashed_password,
        is_admin=(user.email == "admin@plagwise.com")  # 如果是admin@plagwise.com用户，设置为管理员
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# 用户登录
@app.post("/api/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # 添加调试信息
    print(f"Received form data: username={form_data.username}, grant_type={getattr(form_data, 'grant_type', 'N/A')}")
    
    # 验证grant_type（如果提供）
    if hasattr(form_data, 'grant_type') and form_data.grant_type and form_data.grant_type != "password":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only 'password' grant type is supported"
        )
    
    # 使用邮箱登录，form_data.username字段现在包含邮箱
    user = db.query(UserModel).filter(UserModel.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# 测试端点 - 验证API是否正常工作
@app.post("/api/test-token")
async def test_token(request: Request):
    """测试端点，用于验证请求格式"""
    try:
        # 尝试解析form数据
        form = await request.form()
        return {
            "status": "success",
            "message": "Form data received successfully",
            "data": dict(form),
            "content_type": request.headers.get("content-type")
        }
    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to parse form data",
            "error": str(e),
            "content_type": request.headers.get("content-type")
        }

# 获取当前用户信息
@app.get("/api/users/me", response_model=User)
async def read_users_me(current_user: UserModel = Depends(get_current_user)):
    return current_user

@app.post("/webhook/plagwise")
async def plagwise_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        form = await request.form()
        data = dict(form)
        print('webhook data: ', data)
        report_id = data.get('report_id')
        submitted_file_url = data.get('submitted_file_url', '')
        submitted_file = ''
        if submitted_file_url:
            start = submitted_file_url.find('submitted_files/')
            if start != -1:
                start += len('submitted_files/')
                end = submitted_file_url.find('?X-Amz-Algorithm', start)
                if end != -1:
                    submitted_file = submitted_file_url[start:end]
                else:
                    submitted_file = submitted_file_url[start:]
        report = db.query(Report).filter_by(report_id=report_id).first()
        if report:
            # 已存在则更新
            report.status = data.get('status')
            report.error = data.get('error')
            report.submitted_file_url = submitted_file_url
            report.submitted_file = submitted_file
            report.plagiarism_report_url = data.get('plagiarism_report_url')
            report.ai_report_url = data.get('ai_report_url')
            report.similarity_percent = data.get('similarity_percent')
            report.ai_percent = data.get('ai_percent')
            report.slots_balance = data.get('slots_balance')
        else:
            # 不存在则插入
            report = Report(
                report_id=report_id,
                status=data.get('status'),
                error=data.get('error'),
                submitted_file_url=submitted_file_url,
                submitted_file=submitted_file,
                plagiarism_report_url=data.get('plagiarism_report_url'),
                ai_report_url=data.get('ai_report_url'),
                similarity_percent=data.get('similarity_percent'),
                ai_percent=data.get('ai_percent'),
                slots_balance=data.get('slots_balance')
            )
            db.add(report)
        db.commit()
        return {"msg": "success", "data": data}
    except Exception as e:
        print("处理webhook请求失败:", e)
        return {"msg": "fail", "error": str(e)}

router = APIRouter()

class SerialCheckRequest(BaseModel):
    serial: str

@router.post("/api/validate-serial")
def validate_serial(data: SerialCheckRequest, db: Session = Depends(get_db)):
    serial_obj = db.query(SerialNumber).filter(SerialNumber.serial == data.serial).first()
    if not serial_obj:
        raise HTTPException(status_code=400, detail="序列号无效或已被使用")
    db.delete(serial_obj)
    db.commit()
    return {"valid": True}

@router.get("/api/reports")
def get_reports(db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    if not current_user.report_id_list:
        logging.warning(f"用户 {current_user.email} 没有报告")
        return []
    
    report_ids = current_user.report_id_list.split(';')
    
    # 查询数据库中存在的报告
    reports = db.query(Report).filter(Report.report_id.in_(report_ids)).order_by(Report.created_at.desc()).all()
    
    # 找出数据库中缺失的 report_id
    found_report_ids = [r.report_id for r in reports]
    missing_report_ids = [rid for rid in report_ids if rid not in found_report_ids]
    
    if missing_report_ids:
        logging.warning(f"⚠️ 数据库中缺失的 report_ids: {missing_report_ids}")
        logging.warning(f"💡 提示：这些报告可能还在处理中，或者是旧数据")
    
    logging.warning(f"✅ 返回 {len(reports)} 个报告（共 {len(report_ids)} 个ID）")
    return reports

@router.delete("/api/reports/{report_id}")
def delete_report(report_id: str, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    db.delete(report)
    db.commit()
    return {"msg": "deleted"}

# 序列号相关API
class SerialNumberCreate(BaseModel):
    count: int

class SerialNumberResponse(BaseModel):
    serial: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

@app.post("/api/generate-serials", response_model=List[SerialNumberResponse])
def generate_serials(data: SerialNumberCreate, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    # 验证是否是管理员
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="只有管理员可以生成序列号")
    
    # 生成序列号
    serials = []
    for _ in range(data.count):
        serial = str(uuid.uuid4())
        db_serial = SerialNumber(serial=serial, created_at=datetime.utcnow())
        db.add(db_serial)
        serials.append(db_serial)
    
    db.commit()
    for serial in serials:
        db.refresh(serial)
    
    return serials

@app.get("/api/serials", response_model=List[SerialNumberResponse])
def get_serials(db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    # 验证是否是管理员
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="只有管理员可以查看序列号")
    
    # 获取所有序列号
    serials = db.query(SerialNumber).order_by(SerialNumber.created_at.desc()).all()
    return serials

@app.post("/api/users/update-reports")
async def update_user_reports(
    report_data: dict,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        report_id = report_data.get("report_id")
        if not report_id:
            raise HTTPException(status_code=400, detail="Report ID is required")

        # 更新用户的 report_id_list
        if current_user.report_id_list:
            if report_id not in current_user.report_id_list.split(";"):
                current_user.report_id_list = f"{current_user.report_id_list};{report_id}"
        else:
            current_user.report_id_list = report_id

        db.commit()
        return {"status": "success", "message": "Report list updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

app.include_router(router)

# 导出FastAPI应用实例供Vercel使用
# handler = app

# 文件提交转发API
@app.post("/api/submit-file")
async def submit_file_forward(request: Request, db: Session = Depends(get_db)):
    try:
        # 获取原始请求的form数据
        form = await request.form()
        
        # 准备转发到Plagwise的数据
        plagwise_data = aiohttp.FormData()
        
        # 复制所有表单字段
        for key, value in form.items():
            if hasattr(value, 'filename'):  # 文件字段
                content = await value.read()
                plagwise_data.add_field('file', content, filename=value.filename)
            else:  # 普通字段
                plagwise_data.add_field(key, value)
        
        # 转发到Plagwise API
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'https://turnitin-api.easyessayy.com/v2/submissions',
                headers={"Authorization": "Bearer c1f4ae8609e630c29b411054bf4ee918c08d80c360e0388371439c93df43178"},
                data=plagwise_data
            ) as response:
                response_data = await response.json()
                
                # 如果提交成功，立即在数据库中创建初始记录
                if response_data.get('result') and response_data['result'].get('id'):
                    report_id = response_data['result']['id']
                    report_status = response_data['result'].get('status', 'pending')
                    
                    # 检查是否已存在该记录
                    existing_report = db.query(Report).filter_by(report_id=report_id).first()
                    if not existing_report:
                        new_report = Report(
                            report_id=report_id,
                            status=report_status,
                            error=None,
                            submitted_file_url=None,
                            submitted_file=None,
                            plagiarism_report_url=None,
                            ai_report_url=None,
                            similarity_percent=None,
                            ai_percent=None,
                            slots_balance=None
                        )
                        db.add(new_report)
                        db.commit()
                        logging.warning(f"✅ 已创建报告初始记录: {report_id}, 状态: {report_status}")
                
                return response_data
                
    except Exception as e:
        logging.error(f"Error forwarding request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 

# 获取任务状态API（供前端调用）
@app.get("/api/getSubmissionStatus")
async def get_submission_status(id: str, db: Session = Depends(get_db)):
    """
    获取报告提交状态
    参数: id - 报告ID
    """
    try:
        # 转发到Plagwise API
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f'https://turnitin-api.easyessayy.com/v2/submissions/{id}',
                headers={"Authorization": "Bearer c1f4ae8609e630c29b411054bf4ee918c08d80c360e0388371439c93df43178"}
            ) as response:
                response_data = await response.json()
                
                # 如果获取成功，同步更新数据库
                if response_data.get('result'):
                    result_data = response_data['result']
                    update_report_in_db(db, id, result_data)
                    logging.info(f"✅ 从 getSubmissionStatus 更新报告 {id}")
                
                return response_data
                
    except Exception as e:
        logging.error(f"Error getting submission status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 后台定时任务：自动更新报告状态 ====================

async def fetch_report_status(report_id: str):
    """
    从 Plagwise API 获取单个报告的状态
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f'https://turnitin-api.easyessayy.com/v2/submissions/{report_id}',
                headers={"Authorization": "Bearer c1f4ae8609e630c29b411054bf4ee918c08d80c360e0388371439c93df43178"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    # 返回 result 字段中的数据
                    return data.get('result', {})
                else:
                    logging.error(f"❌ 获取报告 {report_id} 状态失败: HTTP {response.status}")
                    return None
    except asyncio.TimeoutError:
        logging.warning(f"⏱️ 获取报告 {report_id} 状态超时")
        return None
    except Exception as e:
        logging.error(f"❌ 获取报告 {report_id} 状态异常: {str(e)}")
        return None

def update_report_in_db(db: Session, report_id: str, status_data: dict):
    """
    更新数据库中的报告状态
    """
    try:
        report = db.query(Report).filter_by(report_id=report_id).first()
        
        # 提取 submitted_file
        submitted_file_url = status_data.get('submitted_file_url', '')
        submitted_file = ''
        if submitted_file_url:
            start = submitted_file_url.find('submitted_files/')
            if start != -1:
                start += len('submitted_files/')
                end = submitted_file_url.find('?X-Amz-Algorithm', start)
                if end != -1:
                    submitted_file = submitted_file_url[start:end]
                else:
                    submitted_file = submitted_file_url[start:]
        
        if report:
            # 更新现有报告
            report.status = status_data.get('status')
            report.error = status_data.get('error')
            report.submitted_file_url = submitted_file_url
            report.submitted_file = submitted_file
            report.plagiarism_report_url = status_data.get('plagiarism_report_url')
            report.ai_report_url = status_data.get('ai_report_url')
            report.similarity_percent = status_data.get('similarity_percent')
            report.ai_percent = status_data.get('ai_percent')
            report.slots_balance = status_data.get('slots_balance')
            
            db.commit()
            logging.info(f"✅ 报告 {report_id} 状态已更新: {status_data.get('status')}")
            return True
        else:
            # 不存在的报告，创建新记录
            logging.warning(f"⚠️ 报告 {report_id} 不存在，自动创建...")
            new_report = Report(
                report_id=report_id,
                status=status_data.get('status'),
                error=status_data.get('error'),
                submitted_file_url=submitted_file_url,
                submitted_file=submitted_file,
                plagiarism_report_url=status_data.get('plagiarism_report_url'),
                ai_report_url=status_data.get('ai_report_url'),
                similarity_percent=status_data.get('similarity_percent'),
                ai_percent=status_data.get('ai_percent'),
                slots_balance=status_data.get('slots_balance')
            )
            db.add(new_report)
            db.commit()
            logging.info(f"✅ 已创建报告 {report_id}: {status_data.get('status')}")
            return True
            
    except Exception as e:
        logging.error(f"❌ 更新报告 {report_id} 失败: {str(e)}")
        db.rollback()
        return False

async def background_task_update_reports():
    """
    后台定时任务：定期检查并更新所有未完成的报告状态
    """
    logging.warning("🚀 后台定时任务已启动：每30秒自动更新报告状态...")
    
    while True:
        db = None
        try:
            # 创建数据库会话（使用 SessionLocal，不是 get_db）
            db = SessionLocal()
            
            # 查询所有未完成的报告（状态不是 'completed' 和 'error'）
            pending_reports = db.query(Report).filter(
                Report.status.notin_(['completed', 'error'])
            ).all()
            
            if not pending_reports:
                logging.info("ℹ️ 暂无待处理的报告")
            else:
                logging.warning(f"🔄 开始检查 {len(pending_reports)} 个待处理报告...")
                
                # 批量获取报告状态
                tasks = [fetch_report_status(report.report_id) for report in pending_reports]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 更新数据库
                updated_count = 0
                for report, status_data in zip(pending_reports, results):
                    if status_data and not isinstance(status_data, Exception):
                        if update_report_in_db(db, report.report_id, status_data):
                            updated_count += 1
                
                logging.warning(f"📊 本次更新完成: {updated_count}/{len(pending_reports)} 个报告已更新")
            
        except Exception as e:
            logging.error(f"❌ 后台任务异常: {str(e)}")
        finally:
            # 确保数据库连接被关闭
            if db is not None:
                try:
                    db.close()
                except Exception as e:
                    logging.error(f"关闭数据库连接失败: {str(e)}")
        
        # 每30秒检查一次
        await asyncio.sleep(30)

# 应用启动时自动启动后台任务
@app.on_event("startup")
async def startup_event():
    """
    应用启动时的事件处理
    """
    print("=" * 60)
    logging.warning("FastAPI startup_event!")
    print("=" * 60)
    
    # 启动后台定时任务
    asyncio.create_task(background_task_update_reports())
    
    print("✅ 所有后台任务已启动")

# 应用关闭时的清理
@app.on_event("shutdown")
async def shutdown_event():
    """
    应用关闭时的事件处理
    """
    print("=" * 60)
    logging.warning("FastAPI shutdown_event!")
    print("=" * 60) 