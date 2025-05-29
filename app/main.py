from fastapi import FastAPI, Request, Depends, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import time

from app.routers import auth, books, users, pages, borrow_orders, notifications, categories, authors, publishers
from app.database.db import engine, get_db
from app.database.models import Base
from app.auth.auth import get_current_active_user
from app.tasks import setup_scheduler

# Tạo thư mục logs nếu chưa tồn tại
Path("logs").mkdir(exist_ok=True)

# Tạo thư mục cho file ảnh nếu chưa tồn tại
Path("static/images/book_covers").mkdir(parents=True, exist_ok=True)

# Khởi tạo ứng dụng FastAPI
app = FastAPI(
    title="Hệ Thống Quản Lý Thư Viện",
    description="API cho ứng dụng mượn và quản lý sách",
    version="1.0.0"
)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount thư mục tĩnh
app.mount("/static", StaticFiles(directory="static"), name="static")

# Định nghĩa templates
templates = Jinja2Templates(directory="templates")

# Thêm các router
app.include_router(auth.router)
app.include_router(books.router)
app.include_router(users.router)
app.include_router(pages.router)
app.include_router(borrow_orders.router)
app.include_router(notifications.router)
app.include_router(categories.router)
app.include_router(authors.router)
app.include_router(publishers.router)
app.include_router(authors.router)
app.include_router(publishers.router)

# Định nghĩa endpoint sức khỏe API
@app.get("/api/health")
async def health():
    """
    Kiểm tra sức khỏe API
    """
    return {"status": "healthy"}

# Thiết lập logging cho ứng dụng
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/app.log")
    ]
)
logger = logging.getLogger(__name__)

# Khởi tạo scheduler từ tasks.py
scheduler = setup_scheduler()

# Middleware để tính thời gian phản hồi API
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

if __name__ == "__main__":
    import uvicorn
    
    # Debug = True trong quá trình phát triển
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
