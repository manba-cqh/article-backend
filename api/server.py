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

from .schemas import User, UserCreate, Token
from .auth import get_password_hash, verify_password, create_access_token, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
from .models import User as UserModel, Report, SerialNumber, DatabaseBase
from .database import engine, get_db

# 创建数据库表
DatabaseBase.metadata.create_all(bind=engine)

app = FastAPI()

# 配置CORS - 支持Vercel部署
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # 前端开发服务器地址
        "https://*.vercel.app",   # Vercel部署的域名
        "https://*.now.sh",       # Vercel旧域名
        os.environ.get("FRONTEND_URL", "https://your-frontend-domain.vercel.app")  # 环境变量配置的前端URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 用户注册
@app.post("/api/register", response_model=User)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    # 检查用户名是否已存在
    db_user = db.query(UserModel).filter(UserModel.username == user.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
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
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        is_admin=(user.username == "plagwise_admin")  # 如果是plagwise_admin用户，设置为管理员
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
    user = db.query(UserModel).filter(UserModel.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

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
        return []
    report_ids = current_user.report_id_list.split(';')
    reports = db.query(Report).filter(Report.report_id.in_(report_ids)).all()
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

# Vercel适配
if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=int(os.environ.get("PORT", 3000)), reload=True) 