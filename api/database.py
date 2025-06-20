from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Supabase 数据库配置
# 使用提供的连接信息
DATABASE_URL = "postgresql://postgres.evufvhbaqntieolsstia:CjzLJ37ATE3oaLeX@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres"

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600
)

# 配置Session，启用自动提交
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    # 配置会话超时
    expire_on_commit=False
)

DatabaseBase = declarative_base()

# 依赖项
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 