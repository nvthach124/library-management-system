"""
Scheduled tasks for the Library Management System
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler

from .database.models import BorrowOrder, Notification, User
from .database.db import SessionLocal
from .utils.notifications import create_notification, notify_user_on_order_due_soon, notify_user_on_order_overdue

# Thiết lập logging
import os
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "tasks.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file)
    ]
)
logger = logging.getLogger(__name__)

def check_due_books():
    """
    Kiểm tra và gửi thông báo cho sách sắp đến hạn (chạy hàng ngày)
    """
    logger.info("Đang chạy kiểm tra sách sắp đến hạn...")
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        
        # Định nghĩa khi nào nên gửi cảnh báo (1 ngày và 3 ngày trước khi đến hạn)
        warning_periods = [1, 3]  # Số ngày trước hạn cần thông báo
        
        for days in warning_periods:
            # Tính ngày cần cảnh báo (cách hạn trả đúng X ngày)
            target_date = now + timedelta(days=days)
            
            # Chọn các đơn có hạn trong khoảng 24 giờ quanh thời điểm cảnh báo
            start_date = target_date - timedelta(hours=12)
            end_date = target_date + timedelta(hours=12)
            
            # Lấy danh sách các đơn mượn đang hoạt động và đến hạn trong khoảng thời gian này
            due_orders = db.query(BorrowOrder).filter(
                BorrowOrder.status == "active",
                BorrowOrder.due_date >= start_date,
                BorrowOrder.due_date <= end_date
            ).all()
            
            logger.info(f"Tìm thấy {len(due_orders)} đơn mượn sắp đến hạn trong {days} ngày")
            
            for order in due_orders:
                # Kiểm tra xem đã gửi thông báo chưa trong 12 giờ qua
                existing_notification = db.query(Notification).filter(
                    Notification.user_id == order.user_id,
                    Notification.title.like(f"Sách sắp đến hạn trả - Đơn #{order.id}%"),
                    Notification.created_at >= now - timedelta(hours=12)
                ).first()
                
                if not existing_notification:
                    # Sử dụng hàm tiện ích tạo thông báo
                    notify_user_on_order_due_soon(db, order, days)
                    logger.info(f"Đã tạo thông báo sắp đến hạn cho đơn #{order.id} ({days} ngày)")
                    logger.info(f"Đã tạo thông báo sắp đến hạn cho đơn #{order.id} ({days} ngày)")
        
        # Kiểm tra sách quá hạn
        overdue_orders = db.query(BorrowOrder).filter(
            BorrowOrder.status == "active",
            BorrowOrder.due_date < now
        ).all()
        
        logger.info(f"Tìm thấy {len(overdue_orders)} đơn mượn quá hạn")
        
        for order in overdue_orders:
            # Đánh dấu đơn là quá hạn
            if order.status != "overdue":
                order.status = "overdue"
                db.commit()
            
            days_overdue = (now - order.due_date).days
            
            # Chỉ gửi thông báo quá hạn mỗi ngày một lần
            existing_notification = db.query(Notification).filter(
                Notification.user_id == order.user_id,
                Notification.title.like(f"Sách đã quá hạn trả - Đơn #{order.id}%"),
                Notification.created_at >= now - timedelta(days=1)
            ).first()
            
            if not existing_notification:
                # Lấy danh sách sách trong đơn
                book_titles = [book.title for book in order.books]
                book_list = ", ".join(book_titles)
                
                # Tạo thông báo
                title = f"Sách đã quá hạn trả - Đơn #{order.id}"
                message = f"⚠️ QUAN TRỌNG: Đơn mượn #{order.id} của bạn đã quá hạn trả {days_overdue} ngày (hạn trả: {order.due_date.strftime('%d/%m/%Y')}). Vui lòng trả sách ngay để tránh bị phạt. Sách: {book_list}"
                
                notification = Notification(
                    user_id=order.user_id,
                    title=title,
                    message=message,
                    type="danger",
                    is_read=False
                )
                db.add(notification)
                db.commit()
                logger.info(f"Đã tạo thông báo quá hạn cho đơn #{order.id} ({days_overdue} ngày)")
    
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra sách sắp đến hạn: {str(e)}")
        db.rollback()
    finally:
        db.close()

def setup_scheduler():
    """
    Thiết lập các tác vụ định kỳ
    """
    try:
        # Tạo scheduler
        scheduler = BackgroundScheduler()
        
        # Thêm các tác vụ
        # Chạy kiểm tra sách sắp đến hạn vào 8:00 sáng mỗi ngày
        scheduler.add_job(check_due_books, 'cron', hour=8, minute=0)
        
        # Chạy kiểm tra sách sắp đến hạn mỗi 12 giờ (8:00 AM và 8:00 PM)
        scheduler.add_job(check_due_books, 'cron', hour='8,20')
        
        # Khởi động scheduler
        scheduler.start()
        logger.info("Đã khởi động scheduler cho các tác vụ định kỳ")
        
        return scheduler
    except Exception as e:
        logger.error(f"Lỗi khi thiết lập scheduler: {str(e)}")
        return None
