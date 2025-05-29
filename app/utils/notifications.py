"""
Utility functions for handling notifications in the Library Management System
"""
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional

from app.database.models import User, Notification, BorrowOrder, Book


def create_notification(db: Session, user_id: int, title: str, message: str, notification_type: str = "info"):
    """
    Create a notification for a user
    
    Args:
        db: Database session
        user_id: User ID to notify
        title: Title of the notification
        message: Message content
        notification_type: Type of notification (info, success, warning, danger)
    
    Returns:
        Notification: The created notification
    """
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=notification_type,
        is_read=False,
        is_hidden=False
    )
    
    db.add(notification)
    db.commit()
    db.refresh(notification)
    
    return notification


def notify_all_admins(db: Session, title: str, message: str, notification_type: str = "info"):
    """
    Create notifications for all active admin users
    
    Args:
        db: Database session
        title: Title of the notification
        message: Message content
        notification_type: Type of notification (info, success, warning, danger)
    
    Returns:
        int: Number of admins notified
    """
    admin_users = db.query(User).filter(User.is_admin == True, User.is_active == True).all()
    
    for admin in admin_users:
        notification = Notification(
            user_id=admin.id,
            title=title,
            message=message,
            type=notification_type,
            is_read=False
        )
        db.add(notification)
    
    db.commit()
    return len(admin_users)


def create_admin_notifications(db: Session, title: str, message: str, notification_type: str = "info"):
    """
    Create notifications for all admin users
    
    Args:
        db: Database session
        title: Title of the notification
        message: Message content
        notification_type: Type of notification (info, success, warning, danger)
    
    Returns:
        List[Notification]: List of created notifications
    """
    admin_users = db.query(User).filter(User.is_admin == True, User.is_active == True).all()
    notifications = []
    
    for admin in admin_users:
        notification = create_notification(
            db=db,
            user_id=admin.id,
            title=title,
            message=message,
            notification_type=notification_type
        )
        notifications.append(notification)
    
    return notifications


def notify_user_on_order_approval(db: Session, order: BorrowOrder):
    """
    Notify a user when their borrow order is approved
    
    Args:
        db: Database session
        order: The approved BorrowOrder
    
    Returns:
        Notification: Created notification
    """
    book_titles = [book.title for book in order.books]
    book_list = ", ".join(book_titles[:3])
    if len(order.books) > 3:
        book_list += f" và {len(order.books) - 3} sách khác"
    
    return create_notification(
        db=db,
        user_id=order.user_id,
        title="Đơn mượn đã được duyệt",
        message=f"Đơn mượn #{order.id} của bạn đã được duyệt. Sách mượn: {book_list}. Hạn trả: {order.due_date.strftime('%d/%m/%Y')}.",
        notification_type="success"
    )


def notify_user_on_order_rejection(db: Session, order: BorrowOrder, reason: str = ""):
    """
    Notify a user when their borrow order is rejected
    
    Args:
        db: Database session
        order: The rejected BorrowOrder
        reason: Reason for rejection (optional)
    
    Returns:
        Notification: Created notification
    """
    book_titles = [book.title for book in order.books]
    book_list = ", ".join(book_titles[:3])
    if len(order.books) > 3:
        book_list += f" và {len(order.books) - 3} sách khác"
    
    message = f"Đơn mượn #{order.id} của bạn đã bị từ chối. Sách: {book_list}."
    if reason:
        message += f" Lý do: {reason}"
    
    return create_notification(
        db=db,
        user_id=order.user_id,
        title="Đơn mượn bị từ chối",
        message=message,
        notification_type="warning"
    )


def notify_admin_on_new_order(db: Session, order: BorrowOrder, user: User):
    """
    Notify admin users when a new borrow order is created
    
    Args:
        db: Database session
        order: The new BorrowOrder
        user: User who created the order
        
    Returns:
        int: Number of admins notified
    """
    book_titles = [book.title for book in order.books]
    book_list = ", ".join(book_titles[:3])
    if len(order.books) > 3:
        book_list += f" và {len(order.books) - 3} sách khác"
    
    return notify_all_admins(
        db=db,
        title="Đơn mượn mới cần duyệt",
        message=f"Đơn mượn #{order.id} từ {user.full_name} đang chờ duyệt. Sách: {book_list}.",
        notification_type="info"
    )


def notify_user_on_order_due_soon(db: Session, order: BorrowOrder, days_left: int):
    """
    Notify a user when their borrowed books are due soon
    
    Args:
        db: Database session
        order: The BorrowOrder that's due soon
        days_left: Number of days until due
    
    Returns:
        Notification: Created notification
    """
    book_titles = [book.title for book in order.books]
    book_list = ", ".join(book_titles[:3])
    if len(order.books) > 3:
        book_list += f" và {len(order.books) - 3} sách khác"
    
    # Determine notification type based on urgency
    notification_type = "warning" if days_left <= 1 else "info"
    
    # Create more urgent message for 1-day warning
    if days_left <= 1:
        title = f"⚠️ Sách sẽ hết hạn NGÀY MAI - Đơn #{order.id}"
        message = f"QUAN TRỌNG: Đơn mượn #{order.id} của bạn sẽ đến hạn trả NGÀY MAI ({order.due_date.strftime('%d/%m/%Y')}). Vui lòng chuẩn bị trả sách: {book_list}"
    else:
        title = f"Sách sắp đến hạn trả - Đơn #{order.id}"
        message = f"Đơn mượn #{order.id} của bạn sẽ đến hạn trả trong {days_left} ngày (hạn trả: {order.due_date.strftime('%d/%m/%Y')}). Sách: {book_list}"
    
    return create_notification(
        db=db,
        user_id=order.user_id,
        title=title,
        message=message,
        notification_type=notification_type
    )


def notify_user_on_order_overdue(db: Session, order: BorrowOrder, days_overdue: int):
    """
    Notify a user when their borrowed books are overdue
    
    Args:
        db: Database session
        order: The BorrowOrder that's overdue
        days_overdue: Number of days overdue
    
    Returns:
        Notification: Created notification
    """
    book_titles = [book.title for book in order.books]
    book_list = ", ".join(book_titles[:3])
    if len(order.books) > 3:
        book_list += f" và {len(order.books) - 3} sách khác"
    
    return create_notification(
        db=db,
        user_id=order.user_id,
        title=f"⚠️ Sách đã quá hạn trả - Đơn #{order.id}",
        message=f"Đơn mượn #{order.id} của bạn đã quá hạn trả {days_overdue} ngày (hạn trả: {order.due_date.strftime('%d/%m/%Y')}). Vui lòng trả sách ngay để tránh bị phạt. Sách: {book_list}",
        notification_type="danger"
    )


def notify_user_on_order_return(db: Session, order: BorrowOrder):
    """
    Notify a user when their books have been successfully returned
    
    Args:
        db: Database session
        order: The returned BorrowOrder
    
    Returns:
        Notification: Created notification
    """
    book_titles = [book.title for book in order.books]
    book_list = ", ".join(book_titles[:3])
    if len(order.books) > 3:
        book_list += f" và {len(order.books) - 3} sách khác"
    
    return create_notification(
        db=db,
        user_id=order.user_id,
        title="Trả sách thành công",
        message=f"Đơn mượn #{order.id} của bạn đã được xử lý trả sách thành công. Sách: {book_list}. Cảm ơn bạn đã sử dụng dịch vụ thư viện!",
        notification_type="success"
    )


def notify_admin_on_order_return(db: Session, order: BorrowOrder, user: User):
    """
    Notify admin users when books are returned
    
    Args:
        db: Database session
        order: The returned BorrowOrder
        user: User who returned the books
        
    Returns:
        int: Number of admins notified
    """
    book_titles = [book.title for book in order.books]
    book_list = ", ".join(book_titles[:3])
    if len(order.books) > 3:
        book_list += f" và {len(order.books) - 3} sách khác"
    
    return notify_all_admins(
        db=db,
        title="Sách đã được trả",
        message=f"Đơn mượn #{order.id} từ {user.full_name} đã được trả. Sách: {book_list}.",
        notification_type="info"
    )


def notify_user_system_maintenance(db: Session, user_id: int, maintenance_time: str, estimated_duration: str):
    """
    Notify a user about system maintenance
    
    Args:
        db: Database session
        user_id: User ID to notify
        maintenance_time: When maintenance will occur
        estimated_duration: How long maintenance is expected to last
    
    Returns:
        Notification: Created notification
    """
    return create_notification(
        db=db,
        user_id=user_id,
        title="Thông báo bảo trì hệ thống",
        message=f"Hệ thống thư viện sẽ được bảo trì vào {maintenance_time}. Thời gian dự kiến: {estimated_duration}. Xin lỗi vì sự bất tiện này.",
        notification_type="warning"
    )


def notify_all_users_system_maintenance(db: Session, maintenance_time: str, estimated_duration: str):
    """
    Notify all active users about system maintenance
    
    Args:
        db: Database session
        maintenance_time: When maintenance will occur
        estimated_duration: How long maintenance is expected to last
    
    Returns:
        int: Number of users notified
    """
    active_users = db.query(User).filter(User.is_active == True).all()
    
    for user in active_users:
        notification = Notification(
            user_id=user.id,
            title="Thông báo bảo trì hệ thống",
            message=f"Hệ thống thư viện sẽ được bảo trì vào {maintenance_time}. Thời gian dự kiến: {estimated_duration}. Xin lỗi vì sự bất tiện này.",
            type="warning",
            is_read=False,
            is_hidden=False
        )
        db.add(notification)
    
    db.commit()
    return len(active_users)


def get_unread_count(db: Session, user_id: int) -> int:
    """
    Get the count of unread notifications for a user
    
    Args:
        db: Database session
        user_id: User ID to check
    
    Returns:
        int: Number of unread notifications
    """
    return db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False
    ).count()


def mark_all_notifications_read(db: Session, user_id: int) -> int:
    """
    Mark all notifications as read for a user
    
    Args:
        db: Database session
        user_id: User ID
    
    Returns:
        int: Number of notifications marked as read
    """
    updated_count = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False
    ).update({Notification.is_read: True})
    
    db.commit()
    return updated_count


def delete_old_notifications(db: Session, days_old: int = 30) -> int:
    """
    Delete notifications older than specified days
    
    Args:
        db: Database session
        days_old: Number of days after which to delete notifications
    
    Returns:
        int: Number of notifications deleted
    """
    from datetime import timedelta
    
    cutoff_date = datetime.utcnow() - timedelta(days=days_old)
    
    deleted_count = db.query(Notification).filter(
        Notification.created_at < cutoff_date
    ).delete()
    
    db.commit()
    return deleted_count