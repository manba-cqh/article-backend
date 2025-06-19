import sys
import uuid
from datetime import datetime
from database import SessionLocal, engine
from models import SerialNumber, Base

def generate_serials(n):
    serials = [str(uuid.uuid4()) for _ in range(n)]
    return serials

def save_serials_to_db(serials):
    db = SessionLocal()
    try:
        for s in serials:
            db.add(SerialNumber(serial=s, created_at=datetime.utcnow()))
        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    # 创建表（如果还没创建）
    Base.metadata.create_all(bind=engine)
    # 获取命令行参数
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    serials = generate_serials(n)
    save_serials_to_db(serials)
    print(f"成功生成并保存 {n} 个序列号！") 