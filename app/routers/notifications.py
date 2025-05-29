from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
from sqlalchemy.sql import func

from app.database.db import get_db
from app.database.models import Notification, User, Borrow, BorrowOrder
from app.auth.auth import get_current_active_user, get_current_admin_user, get_current_user, get_user, SECRET_KEY, ALGORITHM
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, Request

# Định nghĩa các model Pydantic
class NotificationBase(BaseModel):
    title: str
    message: str
    type: str = "info"  # info, warning, danger, success

class NotificationCreate(NotificationBase):
    user_id: int

class NotificationResponse(NotificationBase):
    id: int
    user_id: int
    is_read: bool
    is_hidden: bool
    created_at: datetime
    
    class Config:
        orm_mode = True


# Helper function to get user from request
async def get_current_active_user_from_request(request: Request, db: Session = Depends(get_db)):
    """Get current active user from request cookie"""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Không tìm thấy token xác thực",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token không hợp lệ",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = get_user(db, username)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Người dùng không tồn tại",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tài khoản đã bị khóa",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Helper function to get admin user from request
async def get_current_admin_user_from_request(request: Request, db: Session = Depends(get_db)):
    """Get current admin user from request cookie"""
    user = await get_current_active_user_from_request(request, db)
    
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền thực hiện hành động này",
        )
    
    return user
# Tạo router
router = APIRouter(
    prefix="/api/notifications",
    tags=["notifications"]
)

# Lấy tất cả thông báo của người dùng hiện tại
@router.get("/", response_model=List[NotificationResponse])
async def get_notifications(
    request: Request,
    unread_only: bool = False,
    include_hidden: bool = False,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user_from_request)
):
    """
    Lấy danh sách thông báo của người dùng đăng nhập
    """
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    
    if unread_only:
        query = query.filter(Notification.is_read == False)
    
    if not include_hidden:
        query = query.filter(Notification.is_hidden == False)
    
    notifications = query.order_by(Notification.created_at.desc()).all()
    return notifications

# Đánh dấu thông báo đã đọc (cho người dùng thường)
@router.post("/{notification_id}/read", response_model=dict)
async def mark_notification_read(
    notification_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user_from_request)
):
    """
    Đánh dấu thông báo đã đọc (chỉ thông báo của chính người dùng)
    """
    notification = db.query(Notification).filter(
        Notification.id == notification_id, 
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông báo"
        )
    
    notification.is_read = True
    db.commit()
    
    return {"message": "Đã đánh dấu thông báo là đã đọc"}

# Đánh dấu thông báo đã đọc (cho admin)
@router.post("/admin/{notification_id}/read", response_model=dict)
async def mark_notification_read_admin(
    notification_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user_from_request)
):
    """
    Đánh dấu thông báo đã đọc (admin có thể đánh dấu bất kỳ thông báo nào)
    """
    notification = db.query(Notification).filter(
        Notification.id == notification_id
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông báo"
        )
    
    notification.is_read = True
    db.commit()
    
    return {"message": "Đã đánh dấu thông báo là đã đọc"}

# Đánh dấu tất cả thông báo đã đọc
@router.post("/read-all", response_model=dict)
async def mark_all_notifications_read(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user_from_request)
):
    """
    Đánh dấu tất cả thông báo đã đọc
    """
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({Notification.is_read: True})
    
    db.commit()
    
    return {"message": "Đã đánh dấu tất cả thông báo là đã đọc"}

# Xóa thông báo
@router.delete("/{notification_id}", response_model=dict)
async def delete_notification(
    notification_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user_from_request)
):
    """
    Xóa thông báo
    """
    notification = db.query(Notification).filter(
        Notification.id == notification_id, 
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông báo"
        )
    
    db.delete(notification)
    db.commit()
    
    return {"message": "Đã xóa thông báo"}

# Tạo thông báo
def create_notification(db: Session, user_id: int, title: str, message: str, notification_type: str = "info"):
    """
    Hàm helper tạo thông báo
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

# Tạo thông báo cho admin
@router.post("/admin", response_model=NotificationResponse)
async def create_admin_notification(
    notification: NotificationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user_from_request)
):
    """
    Tạo thông báo (chỉ admin)
    """
    # Kiểm tra người dùng tồn tại không
    user = db.query(User).filter(User.id == notification.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy người dùng"
        )
    
    new_notification = Notification(
        user_id=notification.user_id,
        title=notification.title,
        message=notification.message,
        type=notification.type,
        is_read=False,
        is_hidden=False
    )
    
    db.add(new_notification)
    db.commit()
    db.refresh(new_notification)
    
    return new_notification

# Kiểm tra và gửi thông báo sách sắp đến hạn
def check_due_dates(db: Session):
    """
    Hàm kiểm tra và gửi thông báo cho sách sắp đến hạn trả
    """
    now = datetime.utcnow()
    
    # Định nghĩa khi nào nên gửi cảnh báo (1 ngày và 3 ngày trước khi đến hạn)
    warning_periods = [1, 3]  # Số ngày trước hạn cần thông báo
    
    for days in warning_periods:
        # Tính ngày cần cảnh báo (cách hạn trả đúng X ngày)
        target_date = now + timedelta(days=days)
        
        # Chọn các đơn có hạn trong khoảng 24 giờ quanh thời điểm cảnh báo
        # (để không bỏ sót các đơn do sai lệch giờ trong ngày)
        start_date = target_date - timedelta(hours=12)
        end_date = target_date + timedelta(hours=12)
        
        # Lấy danh sách các đơn mượn đang hoạt động và đến hạn trong khoảng thời gian này
        due_orders = db.query(BorrowOrder).filter(
            BorrowOrder.status == "active",
            BorrowOrder.due_date >= start_date,
            BorrowOrder.due_date <= end_date
        ).all()
        
        for order in due_orders:
            # Kiểm tra xem đã gửi thông báo chưa trong 12 giờ qua
            existing_notification = db.query(Notification).filter(
                Notification.user_id == order.user_id,
                Notification.title.like(f"Sách sắp đến hạn trả - Đơn #{order.id}%"),
                Notification.created_at >= now - timedelta(hours=12)
            ).first()
            
            if not existing_notification:
                # Lấy danh sách sách trong đơn
                book_titles = [book.title for book in order.books]
                book_list = ", ".join(book_titles)
                
                # Tạo thông báo với mức độ cảnh báo phù hợp
                title = f"Sách sắp đến hạn trả - Đơn #{order.id}"
                
                # Điều chỉnh thông điệp dựa trên số ngày còn lại
                if days == 1:
                    message = f"⚠️ QUAN TRỌNG: Đơn mượn #{order.id} của bạn sẽ đến hạn trả NGÀY MAI ({order.due_date.strftime('%d/%m/%Y')}). Vui lòng chuẩn bị trả sách. Sách: {book_list}"
                    notification_type = "warning"
                else:
                    message = f"Đơn mượn #{order.id} của bạn sẽ đến hạn trả trong {days} ngày (hạn trả: {order.due_date.strftime('%d/%m/%Y')}). Sách: {book_list}"
                    notification_type = "info"
                
                create_notification(
                    db=db,
                    user_id=order.user_id,
                    title=title,
                    message=message,
                    notification_type=notification_type
                )

# Kiểm tra và gửi thông báo sách quá hạn
def check_overdue_books(db: Session):
    """
    Hàm kiểm tra và gửi thông báo cho sách đã quá hạn trả
    """
    now = datetime.utcnow()
    
    # Lấy danh sách các đơn mượn đang hoạt động và đã quá hạn
    overdue_orders = db.query(BorrowOrder).filter(
        BorrowOrder.status == "active",
        BorrowOrder.due_date < now
    ).all()
    
    for order in overdue_orders:
        # Đánh dấu đơn là quá hạn
        if order.status != "overdue":
            order.status = "overdue"
            db.commit()
        
        days_overdue = (now - order.due_date).days
        
        # Kiểm tra xem đã gửi thông báo chưa
        existing_notification = db.query(Notification).filter(
            Notification.user_id == order.user_id,
            Notification.title.like(f"Sách đã quá hạn trả - Đơn #{order.id}%"),
            Notification.created_at >= now - timedelta(days=1)  # Chỉ kiểm tra thông báo trong 1 ngày gần đây
        ).first()
        
        if not existing_notification:
            # Lấy danh sách sách trong đơn
            book_titles = [book.title for book in order.books]
            book_list = ", ".join(book_titles)
            
            # Tạo thông báo
            title = f"Sách đã quá hạn trả - Đơn #{order.id}"
            message = f"Đơn mượn #{order.id} của bạn đã quá hạn trả {days_overdue} ngày (hạn trả: {order.due_date.strftime('%d/%m/%Y')}). Vui lòng trả sách ngay để tránh bị phạt. Sách: {book_list}"
            
            create_notification(
                db=db,
                user_id=order.user_id,
                title=title,
                message=message,
                notification_type="danger"
            )

# Chạy kiểm tra thông báo (manual trigger for testing)
@router.post("/admin/check-notifications", response_model=dict)
async def run_notification_checks(
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user_from_request)
):
    """
    Chạy kiểm tra và gửi thông báo hạn trả sách (chỉ admin)
    """
    try:
        # Chạy kiểm tra ngay lập tức
        check_due_dates(db)
        check_overdue_books(db)
        
        return {"message": "Đã hoàn thành kiểm tra và gửi thông báo"}
    except Exception as e:
        return {"message": f"Có lỗi xảy ra: {str(e)}"}

# Hàm helper để gửi thông báo cho tất cả admin
def notify_all_admins(db: Session, title: str, message: str, notification_type: str = "info"):
    """
    Gửi thông báo cho tất cả admin
    """
    admin_users = db.query(User).filter(User.is_admin == True, User.is_active == True).all()
    
    for admin in admin_users:
        notification = Notification(
            user_id=admin.id,
            title=title,
            message=message,
            type=notification_type,
            is_read=False,
            is_hidden=False
        )
        db.add(notification)
    
    db.commit()
    return len(admin_users)

# Đếm số thông báo chưa đọc
@router.get("/unread-count", response_model=dict)
async def get_unread_count(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user_from_request)
):
    """
    Đếm số thông báo chưa đọc (không bao gồm đã ẩn)
    """
    count = db.query(func.count(Notification.id)).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
        Notification.is_hidden == False
    ).scalar()
    
    return {"count": count}

# Test endpoint to create sample notifications
@router.post("/test/create-sample", response_model=dict)
async def create_sample_notifications(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user_from_request)
):
    """
    Tạo thông báo mẫu để test (chỉ dành cho admin hoặc development)
    """
    # Create sample notifications for testing
    sample_notifications = [
        {
            "title": "Chào mừng bạn đến với hệ thống thư viện!",
            "message": "Cảm ơn bạn đã sử dụng dịch vụ thư viện. Hãy khám phá các tính năng mới và tìm kiếm những cuốn sách yêu thích của bạn.",
            "type": "success"
        },
        {
            "title": "Sách sắp đến hạn trả",
            "message": "Bạn có 2 cuốn sách sẽ đến hạn trả trong 3 ngày nữa. Vui lòng chuẩn bị trả sách đúng hạn để tránh bị phạt.",
            "type": "warning"
        },
        {
            "title": "Có sách mới về chủ đề công nghệ",
            "message": "Thư viện vừa cập nhật 15 cuốn sách mới về lập trình, AI và khoa học máy tính. Hãy đến mượn ngay!",
            "type": "info"
        },
        {
            "title": "Thông báo bảo trì hệ thống",
            "message": "Hệ thống sẽ được bảo trì vào 2:00 - 4:00 sáng ngày mai. Trong thời gian này, bạn có thể không truy cập được một số chức năng.",
            "type": "warning"
        }
    ]
    
    created_count = 0
    for notification_data in sample_notifications:
        notification = create_notification(
            db=db,
            user_id=current_user.id,
            title=notification_data["title"],
            message=notification_data["message"],
            notification_type=notification_data["type"]
        )
        created_count += 1
    
    return {
        "message": f"Đã tạo {created_count} thông báo mẫu thành công",
        "count": created_count
    }

# Ẩn thông báo
@router.post("/{notification_id}/hide", response_model=dict)
async def hide_notification(
    notification_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user_from_request)
):
    """
    Ẩn thông báo khỏi danh sách chính (không xóa hoàn toàn)
    """
    notification = db.query(Notification).filter(
        Notification.id == notification_id, 
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông báo"
        )
    
    notification.is_hidden = True
    notification.is_read = True  # Cũng đánh dấu đã đọc
    db.commit()
    
    return {"message": "Đã ẩn thông báo"}

# Hiện lại thông báo
@router.delete("/{notification_id}/hide", response_model=dict)
async def unhide_notification(
    notification_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user_from_request)
):
    """
    Hiện lại thông báo đã ẩn
    """
    notification = db.query(Notification).filter(
        Notification.id == notification_id, 
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông báo"
        )
    
    notification.is_hidden = False
    db.commit()
    
    return {"message": "Đã hiện lại thông báo"}

# Hiện lại tất cả thông báo đã ẩn
@router.post("/unhide-all", response_model=dict)
async def unhide_all_notifications(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user_from_request)
):
    """
    Hiện lại tất cả thông báo đã ẩn
    """
    updated_count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_hidden == True
    ).update({Notification.is_hidden: False})
    
    db.commit()
    
    return {"message": f"Đã hiện lại {updated_count} thông báo"}

# Admin endpoints for individual notification management
@router.post("/admin/{notification_id}/hide")
async def admin_hide_notification(
    notification_id: int, 
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Ẩn một thông báo cụ thể (admin only)
    """
    current_user = await get_current_active_user_from_request(request, db)
    
    # Kiểm tra quyền admin
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền thực hiện thao tác này"
        )
    
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông báo"
        )
    
    notification.is_hidden = True
    db.commit()
    
    return {"success": True, "message": "Đã ẩn thông báo"}

@router.post("/admin/{notification_id}/show")
async def admin_show_notification(
    notification_id: int, 
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Hiển thị lại một thông báo đã ẩn (admin only)
    """
    current_user = await get_current_active_user_from_request(request, db)
    
    # Kiểm tra quyền admin
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền thực hiện thao tác này"
        )
    
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông báo"
        )
    
    notification.is_hidden = False
    db.commit()
    
    return {"success": True, "message": "Đã hiển thị lại thông báo"}

@router.delete("/admin/{notification_id}")
async def admin_delete_notification(
    notification_id: int, 
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Xóa một thông báo (admin only)
    """
    current_user = await get_current_active_user_from_request(request, db)
    
    # Kiểm tra quyền admin
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền thực hiện thao tác này"
        )
    
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông báo"
        )
    
    db.delete(notification)
    db.commit()
    
    return {"success": True, "message": "Đã xóa thông báo"}

@router.get("/admin/{notification_id}")
async def admin_get_notification_detail(
    notification_id: int, 
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Lấy chi tiết một thông báo (admin only)
    """
    current_user = await get_current_active_user_from_request(request, db)
    
    # Kiểm tra quyền admin
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền thực hiện thao tác này"
        )
    
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông báo"
        )
    
    # Lấy thông tin user
    user = db.query(User).filter(User.id == notification.user_id).first()
    
    return {
        "id": notification.id,
        "title": notification.title,
        "message": notification.message,
        "type": notification.type,
        "is_read": notification.is_read,
        "is_hidden": notification.is_hidden,
        "created_at": notification.created_at,
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email
        }
    }
