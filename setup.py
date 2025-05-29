#!/usr/bin/env python3
"""
Script để thiết lập và khởi tạo database cho hệ thống quản lý thư viện.
Chạy script này để tạo cấu trúc database và dữ liệu mẫu.
"""

import sys
import os
import argparse

def main():
    parser = argparse.ArgumentParser(description='Thiết lập và khởi tạo database cho hệ thống quản lý thư viện')
    parser.add_argument('--reset', action='store_true', help='Xóa và tạo lại dữ liệu mẫu')
    args = parser.parse_args()
    
    try:
        # Tạo thư mục static nếu chưa tồn tại
        os.makedirs('static/images/book_covers', exist_ok=True)
        print("Đã tạo thư mục static/images/book_covers")
        
        from app.database.init_db import init_db
        
        # Khởi tạo database
        init_db()
        print("Đã thiết lập database thành công!")
        print("-" * 50)
        print("Bạn có thể chạy ứng dụng bằng lệnh:")
        print("uvicorn app.main:app --reload")
        print("-" * 50)
        print("Tài khoản mặc định:")
        print("Admin: admin / admin123")
        print("User: user / user123")
    except Exception as e:
        print(f"Lỗi: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
 