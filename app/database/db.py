from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Tải các biến môi trường từ file .env
load_dotenv()

# Thông tin kết nối database
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "library_db")

# Tạo URL kết nối
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Tạo engine để kết nối đến database
engine = create_engine(DATABASE_URL)

# Tạo SessionLocal để tương tác với database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Tạo Base cho models
Base = declarative_base()

# Dependency để lấy database session
def get_db():
    """
    Tạo và quản lý database session.
    Hàm này sẽ được sử dụng như một dependency trong FastAPI.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
 