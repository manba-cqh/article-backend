from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(100))
    is_admin = Column(Boolean, default=False)
    report_id_list = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SerialNumber(Base):
    __tablename__ = "serial_numbers"
    id = Column(Integer, primary_key=True, index=True)
    serial = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Report(Base):
    __tablename__ = "reports"
    report_id = Column(String, primary_key=True, index=True)
    status = Column(String)
    error = Column(String)
    submitted_file_url = Column(String)
    submitted_file = Column(String)
    plagiarism_report_url = Column(String)
    ai_report_url = Column(String)
    similarity_percent = Column(String)
    ai_percent = Column(String)
    slots_balance = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow) 