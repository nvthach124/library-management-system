# 📚 Library Management System

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![MySQL](https://img.shields.io/badge/MySQL-8.0+-orange.svg)](https://mysql.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/Code%20Style-black-black.svg)](https://github.com/psf/black)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#-đóng-góp)

> **Hệ thống quản lý thư viện hiện đại** được xây dựng với FastAPI, SQLAlchemy và Bootstrap. Dự án này cung cấp một giải pháp toàn diện cho việc quản lý thư viện với giao diện thân thiện và hiệu suất cao.

**🌟 Nếu dự án này hữu ích, hãy cho một star ⭐ để ủng hộ nhé!**

## ✨ Tính năng nổi bật

### 👤 Dành cho người dùng
- **🔐 Xác thực**: Đăng ký, đăng nhập với JWT Token
- **🔍 Tìm kiếm thông minh**: Tìm sách theo tên, tác giả, thể loại, năm xuất bản
- **📖 Chi tiết sách**: Giao diện hiện đại với hình ảnh bìa sách
- **🛒 Giỏ mượn sách**: Quản lý đơn mượn với tối đa 5 cuốn/đơn
- **📊 Lịch sử cá nhân**: Theo dõi các đơn mượn hiện tại và đã trả
- **🔔 Thông báo**: Nhận cảnh báo hạn trả, thông báo hệ thống
- **👨‍💼 Quản lý hồ sơ**: Cập nhật thông tin cá nhân

### 🛡️ Dành cho quản trị viên
- **📚 Quản lý sách**: CRUD sách với upload ảnh bìa
- **🏷️ Quản lý danh mục**: Thể loại, tác giả, nhà xuất bản
- **👥 Quản lý người dùng**: Xem, chỉnh sửa, khóa/mở khóa tài khoản
- **📋 Quản lý đơn mượn**: Duyệt, từ chối, xác nhận trả sách
- **📈 Báo cáo thống kê**: Dashboard với biểu đồ và số liệu
- **⚠️ Quản lý quá hạn**: Theo dõi sách quá hạn và phạt
- **🔔 Hệ thống thông báo**: Gửi thông báo tự động và thủ công

## 🛠️ Công nghệ sử dụng

- **🚀 Backend**: FastAPI 0.103.1, Python 3.8+
- **🗄️ Database**: MySQL 8.0+ với SQLAlchemy ORM
- **🔒 Authentication**: JWT Token với passlib
- **🎨 Frontend**: HTML5, CSS3, JavaScript ES6+, Bootstrap 5
- **📁 File Upload**: Python-multipart cho upload ảnh
- **⏰ Task Scheduler**: APScheduler cho thông báo tự động
- **🎭 Template Engine**: Jinja2
- **📧 Validation**: Pydantic models, email-validator
- **🧪 Testing**: Pytest, HTTPx
- **🌍 CORS**: FastAPI CORS middleware


## 📋 Yêu cầu hệ thống

- **Python**: 3.8+ (Khuyến nghị 3.10+)
- **MySQL**: 8.0+ hoặc MariaDB 10.5+
- **RAM**: Tối thiểu 2GB (Khuyến nghị 4GB+)
- **Dung lượng**: 500MB cho ứng dụng + 1GB cho database
- **Hệ điều hành**: Windows 10+, Ubuntu 20.04+, macOS 10.15+


## 🚀 Hướng dẫn cài đặt

### 🪟 Trên Windows

#### Bước 1: Cài đặt các phần mềm cần thiết

1. **Cài đặt Python**
   - Tải Python từ: https://www.python.org/downloads/
   - Chọn phiên bản 3.8 hoặc cao hơn
   - ⚠️ **Quan trọng**: Tick vào "Add Python to PATH" khi cài đặt
   - Kiểm tra cài đặt:
     ```cmd
     python --version
     pip --version
     ```

2. **Cài đặt MySQL**
   - Tải MySQL Community Server từ: https://dev.mysql.com/downloads/mysql/
   - Cài đặt MySQL Workbench để quản lý database
   - Ghi nhớ username/password của root user

3. **Cài đặt Git (tùy chọn)**
   - Tải từ: https://git-scm.com/download/win

#### Bước 2: Tải và thiết lập dự án

1. **Clone hoặc tải dự án**
   ```cmd
   # Nếu có Git
   git clone https://github.com/nvthach124/library-management-system.git
   cd library-management-system
   
   # Hoặc tải file ZIP và giải nén
   ```

2. **Tạo môi trường ảo Python**
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Cài đặt thư viện**
   ```cmd
   pip install -r requirements.txt
   ```

#### Bước 3: Cấu hình Database

1. **Tạo database trong MySQL**
   ```sql
   -- Mở MySQL Workbench hoặc command line
   CREATE DATABASE library_management CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

2. **Tạo file cấu hình môi trường**
   - Tạo file `.env` trong thư mục gốc:
   ```env
   # Database Configuration
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=your_mysql_password
   DB_NAME=library_management
   
   # JWT Configuration
   SECRET_KEY=your-secret-key-here
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   
   # File Upload
   UPLOAD_DIR=static/images/book_covers/
   MAX_FILE_SIZE=5242880
   ```

3. **Khởi tạo database**
   ```cmd
   python app/database/init_db.py
   ```

#### Bước 4: Chạy ứng dụng

```cmd
# Đảm bảo môi trường ảo đã được kích hoạt
venv\Scripts\activate

# Chạy server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

### 🐧 Trên Ubuntu

#### Bước 1: Cập nhật hệ thống và cài đặt các phần mềm cần thiết

1. **Cập nhật package list**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. **Cài đặt Python và pip**
   ```bash
   sudo apt install python3 python3-pip python3-venv python3-dev -y
   
   # Kiểm tra phiên bản
   python3 --version
   pip3 --version
   ```

3. **Cài đặt MySQL Server**
   ```bash
   sudo apt install mysql-server mysql-client -y
   
   # Bảo mật MySQL
   sudo mysql_secure_installation
   
   # Kiểm tra dịch vụ
   sudo systemctl status mysql
   ```

4. **Cài đặt các gói hỗ trợ**
   ```bash
   sudo apt install build-essential libmysqlclient-dev pkg-config -y
   ```

#### Bước 2: Tải và thiết lập dự án

1. **Clone hoặc tải dự án**
   ```bash
   # Cài đặt Git nếu chưa có
   sudo apt install git -y
   
   # Clone dự án
   git clone https://github.com/nvthach124/library-management-system.git
   cd library-management-system
   
   # Hoặc tải và giải nén file ZIP
   ```

2. **Tạo môi trường ảo Python**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Cài đặt thư viện**
   ```bash
   pip install -r requirements.txt
   ```

#### Bước 3: Cấu hình Database

1. **Tạo database trong MySQL**
   ```bash
   # Đăng nhập MySQL
   sudo mysql -u root -p
   
   # Tạo database
   CREATE DATABASE library_management CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   
   # Tạo user cho ứng dụng (tùy chọn)
   CREATE USER 'libuser'@'localhost' IDENTIFIED BY 'secure_password';
   GRANT ALL PRIVILEGES ON library_management.* TO 'libuser'@'localhost';
   FLUSH PRIVILEGES;
   EXIT;
   ```

2. **Tạo file cấu hình môi trường**
   ```bash
   # Tạo file .env
   nano .env
   
   # Hoặc sử dụng editor khác
   vim .env
   ```
   
   Nội dung file `.env`:
   ```env
   # Database Configuration
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=libuser
   DB_PASSWORD=your_mysql_password
   DB_NAME=library_management
   
   # JWT Configuration
   SECRET_KEY=your-very-secret-key-here
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   
   # File Upload
   UPLOAD_DIR=static/images/book_covers/
   MAX_FILE_SIZE=5242880
   ```

3. **Khởi tạo database**
   ```bash
   python app/database/init_db.py
   ```

#### Bước 4: Chạy ứng dụng

```bash
# Đảm bảo môi trường ảo đã được kích hoạt
source venv/bin/activate

# Chạy server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Bước 5: Thiết lập chạy tự động (tùy chọn)

1. **Tạo systemd service**
   ```bash
   sudo nano /etc/systemd/system/library-system.service
   ```

2. **Nội dung service file**
   ```ini
   [Unit]
   Description=Library Management System
   After=network.target mysql.service
   
   [Service]
   Type=simple
   User=your-username
   WorkingDirectory=/path/to/library-management-system
   Environment=PATH=/path/to/library-management-system/venv/bin
   ExecStart=/path/to/library-management-system/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
   Restart=always
   
   [Install]
   WantedBy=multi-user.target
   ```

3. **Kích hoạt service**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable library-system
   sudo systemctl start library-system
   sudo systemctl status library-system
   ```

---

## 🌐 Truy cập ứng dụng

Sau khi khởi động thành công, truy cập ứng dụng tại:
- **URL**: http://localhost:8000
- **Tài khoản admin mặc định**:
  - Username: `admin`
  - Password: `admin123`

## 📁 Cấu trúc dự án

```
LMSystem/
├── app/                          # Mã nguồn backend
│   ├── auth/                     # Xác thực và phân quyền
│   ├── database/                 # Kết nối và model database
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── db.py                # Database connection
│   │   └── init_db.py           # Database initialization
│   ├── routers/                  # API endpoints
│   │   ├── auth.py              # Authentication APIs
│   │   ├── books.py             # Book management APIs
│   │   ├── users.py             # User management APIs
│   │   ├── pages.py             # Page rendering
│   │   └── ...                  # Other routers
│   ├── utils/                    # Tiện ích và helpers
│   └── main.py                   # FastAPI application
├── static/                       # File tĩnh
│   ├── css/                      # Stylesheets
│   ├── js/                       # JavaScript files
│   └── images/                   # Images và uploads
├── templates/                    # Jinja2 templates
│   ├── admin/                    # Admin templates
│   ├── components/               # Reusable components
│   └── *.html                    # Page templates
├── logs/                         # Log files
├── requirements.txt              # Python dependencies
├── .env                          # Environment configuration
└── README.md                     # Documentation
```

## 🔧 Troubleshooting

### Lỗi thường gặp và cách khắc phục

1. **Lỗi kết nối MySQL**
   ```
   sqlalchemy.exc.OperationalError: (MySQLdb._exceptions.OperationalError)
   ```
   - Kiểm tra MySQL service đang chạy
   - Xác nhận thông tin kết nối trong file `.env`
   - Đảm bảo database đã được tạo

2. **Lỗi port đã được sử dụng**
   ```
   OSError: [Errno 98] Address already in use
   ```
   - Thay đổi port trong lệnh chạy: `--port 8001`
   - Hoặc kill process đang sử dụng port 8000

3. **Lỗi missing dependencies**
   ```
   ModuleNotFoundError: No module named 'fastapi'
   ```
   - Đảm bảo đã kích hoạt virtual environment
   - Chạy lại: `pip install -r requirements.txt`

4. **Lỗi upload file**
   - Kiểm tra quyền ghi trong thư mục `static/images/book_covers/`
   - Đảm bảo thư mục tồn tại

### Kiểm tra logs

```bash
# Xem logs ứng dụng
tail -f logs/app.log

# Xem logs tasks
tail -f logs/tasks.log
```

## 🤝 Đóng góp

Dự án này được phát triển với mục đích học tập. Mọi đóng góp đều được hoan nghênh!

## 📄 License

Dự án này được phát hành dưới giấy phép MIT.

---

**Chúc bạn sử dụng ứng dụng vui vẻ! 📚✨** 
 