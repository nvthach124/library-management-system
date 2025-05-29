from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from sqlalchemy import func

from app.database.db import get_db
from app.database.models import User, Book, Borrow, BorrowOrder, Notification
from app.auth.auth import get_current_active_user, get_current_admin_user, get_password_hash

# Định nghĩa các model Pydantic
class UserBase(BaseModel):
    full_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    address: Optional[str] = None
    
class UserCreate(UserBase):
    username: str
    password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    
class PasswordChange(BaseModel):
    old_password: str
    new_password: str

class PasswordReset(BaseModel):
    new_password: str

class UserResponse(UserBase):
    id: int
    username: str
    is_admin: bool
    is_active: bool
    
    class Config:
        orm_mode = True

class UserAdminUpdate(BaseModel):
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    notes: Optional[str] = None

class UserProfile(UserBase):
    phone_number: Optional[str] = None
    is_active: bool
    is_admin: bool
    
    class Config:
        orm_mode = True

class UserWithStats(UserProfile):
    active_borrows_count: int
    overdue_borrows_count: int
    returned_borrows_count: int
    
    class Config:
        orm_mode = True

# Tạo router
router = APIRouter(
    prefix="/api/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
)

@router.get("/me", response_model=UserProfile)
async def get_current_user_info(
    current_user = Depends(get_current_active_user)
):
    """
    Lấy thông tin người dùng hiện tại
    """
    return current_user

@router.put("/me", response_model=UserProfile)
async def update_current_user(
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Cập nhật thông tin người dùng hiện tại
    """
    # Kiểm tra email đã tồn tại chưa
    if user_data.email and user_data.email != current_user.email:
        user_exists = db.query(User).filter(User.email == user_data.email).first()
        if user_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email đã được sử dụng"
            )
        current_user.email = user_data.email
    
    if user_data.full_name:
        current_user.full_name = user_data.full_name
    
    if user_data.phone_number:
        current_user.phone_number = user_data.phone_number
    
    if user_data.address:
        current_user.address = user_data.address
    
    # Lưu vào database
    db.commit()
    db.refresh(current_user)
    
    return current_user

@router.post("/me/change-password", response_model=dict)
async def change_password(
    password_data: PasswordChange,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Đổi mật khẩu người dùng hiện tại
    """
    from app.auth.auth import verify_password
    
    # Kiểm tra mật khẩu cũ
    if not verify_password(password_data.old_password, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu hiện tại không đúng"
        )
    
    # Cập nhật mật khẩu mới
    current_user.password = get_password_hash(password_data.new_password)
    
    # Lưu vào database
    db.commit()
    
    return {"message": "Đã đổi mật khẩu thành công"}

@router.get("/me/borrows", response_model=dict)
async def get_current_user_borrows(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Lấy thông tin các sách đang mượn, lịch sử mượn của người dùng hiện tại
    """
    # Lấy các đơn mượn
    orders_query = db.query(BorrowOrder).filter(BorrowOrder.user_id == current_user.id)
    
    # Lọc theo trạng thái nếu được chỉ định
    if status:
        orders_query = orders_query.filter(BorrowOrder.status == status)
    
    orders = orders_query.order_by(BorrowOrder.order_date.desc()).all()
    
    # Phân loại đơn mượn
    pending_orders = [order for order in orders if order.status == "pending"]
    active_orders = [order for order in orders if order.status in ["active", "overdue"]]
    completed_orders = [order for order in orders if order.status in ["completed", "rejected", "cancelled"]]
    
    # Đếm số sách đang mượn, đã trả
    total_books_borrowed = db.query(func.count(Borrow.id)).filter(
        Borrow.user_id == current_user.id
    ).scalar()
    
    total_books_returned = db.query(func.count(Borrow.id)).filter(
        Borrow.user_id == current_user.id,
        Borrow.is_returned == True
    ).scalar()
    
    total_books_overdue = db.query(func.count(Borrow.id)).filter(
        Borrow.user_id == current_user.id,
        Borrow.status == "overdue"
    ).scalar()
    
    return {
        "statistics": {
            "total_books_borrowed": total_books_borrowed,
            "total_books_returned": total_books_returned,
            "total_books_overdue": total_books_overdue,
            "total_orders": len(orders),
            "pending_orders": len(pending_orders),
            "active_orders": len(active_orders),
            "completed_orders": len(completed_orders)
        },
        "orders": {
            "pending": pending_orders,
            "active": active_orders,
            "history": completed_orders
        }
    }

# API cho admin
@router.get("/admin/users", response_model=List[UserResponse])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    Lấy danh sách tất cả người dùng (chỉ admin)
    """
    query = db.query(User)
    
    # Tìm kiếm theo tên, email, username
    if search:
        query = query.filter(
            (User.full_name.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%")) |
            (User.username.ilike(f"%{search}%"))
        )
    
    # Lọc theo trạng thái nếu được chỉ định
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    users = query.offset(skip).limit(limit).all()
    
    return users

@router.get("/admin/users/{user_id}", response_model=UserResponse)
async def get_user_detail(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    Lấy thông tin chi tiết của một người dùng (chỉ admin)
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy người dùng"
        )
    
    return user

@router.put("/admin/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserAdminUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    Cập nhật thông tin người dùng (chỉ admin)
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy người dùng"
        )
    
    # Cập nhật trạng thái người dùng
    if user_data.is_active is not None:
        previous_state = user.is_active
        user.is_active = user_data.is_active
        
        # Nếu khóa tài khoản, tạo thông báo cho người dùng
        if previous_state == True and user_data.is_active == False:
            notification = Notification(
                user_id=user.id,
                title="Tài khoản đã bị khóa",
                message="Tài khoản của bạn đã bị khóa do vi phạm quy định của thư viện. Vui lòng liên hệ quản trị viên để biết thêm chi tiết.",
                type="danger"
            )
            db.add(notification)
        
        # Nếu mở khóa tài khoản, tạo thông báo cho người dùng
        if previous_state == False and user_data.is_active == True:
            notification = Notification(
                user_id=user.id,
                title="Tài khoản đã được mở khóa",
                message="Tài khoản của bạn đã được mở khóa. Bạn có thể tiếp tục sử dụng các dịch vụ của thư viện.",
                type="info"
            )
            db.add(notification)
    
    # Cập nhật vai trò admin
    if user_data.is_admin is not None:
        user.is_admin = user_data.is_admin
    
    # Lưu vào database
    db.commit()
    db.refresh(user)
    
    return user

@router.post("/admin/users/{user_id}/lock", response_model=dict)
async def lock_user_account(
    user_id: int,
    reason: str = Query(..., description="Lý do khóa tài khoản"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    Khóa tài khoản người dùng (chỉ admin)
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy người dùng"
        )
    
    # Không thể khóa tài khoản admin
    if user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể khóa tài khoản quản trị viên"
        )
    
    # Khóa tài khoản
    user.is_active = False
    
    # Tạo thông báo cho người dùng
    notification = Notification(
        user_id=user.id,
        title="Tài khoản đã bị khóa",
        message=f"Tài khoản của bạn đã bị khóa với lý do: {reason}. Vui lòng liên hệ quản trị viên để biết thêm chi tiết.",
        type="danger"
    )
    db.add(notification)
    
    # Lưu vào database
    db.commit()
    
    return {"message": f"Đã khóa tài khoản người dùng {user.username}"}

@router.post("/admin/users/{user_id}/unlock", response_model=dict)
async def unlock_user_account(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    Mở khóa tài khoản người dùng (chỉ admin)
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy người dùng"
        )
    
    # Mở khóa tài khoản
    user.is_active = True
    
    # Tạo thông báo cho người dùng
    notification = Notification(
        user_id=user.id,
        title="Tài khoản đã được mở khóa",
        message="Tài khoản của bạn đã được mở khóa. Bạn có thể tiếp tục sử dụng các dịch vụ của thư viện.",
        type="info"
    )
    db.add(notification)
    
    # Lưu vào database
    db.commit()
    
    return {"message": f"Đã mở khóa tài khoản người dùng {user.username}"}

@router.get("/admin/all", response_model=List[UserWithStats])
async def get_all_users(
    skip: int = 0, 
    limit: int = 100,
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Lấy danh sách tất cả người dùng (chỉ admin)
    """
    query = db.query(User)
    
    # Áp dụng bộ lọc tìm kiếm
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.full_name.ilike(search_term)) | 
            (User.email.ilike(search_term))
        )
    
    # Áp dụng bộ lọc trạng thái
    if status == "active":
        query = query.filter(User.is_active == True)
    elif status == "inactive":
        query = query.filter(User.is_active == False)
    
    users = query.offset(skip).limit(limit).all()
    
    # Lấy thống kê cho từng người dùng
    result = []
    for user in users:
        # Đếm sách đang mượn
        active_borrows_count = db.query(func.count(Borrow.id)).filter(
            Borrow.user_id == user.id,
            Borrow.is_returned == False
        ).scalar() or 0
        
        # Đếm sách quá hạn
        overdue_borrows_count = db.query(func.count(Borrow.id)).join(BorrowOrder).filter(
            Borrow.user_id == user.id,
            Borrow.is_returned == False,
            BorrowOrder.status == "overdue"
        ).scalar() or 0
        
        # Đếm sách đã trả
        returned_borrows_count = db.query(func.count(Borrow.id)).filter(
            Borrow.user_id == user.id,
            Borrow.is_returned == True
        ).scalar() or 0
        
        user_with_stats = UserWithStats(
            email=user.email,
            full_name=user.full_name,
            phone_number=user.phone_number,
            is_active=user.is_active,
            is_admin=user.is_admin,
            active_borrows_count=active_borrows_count,
            overdue_borrows_count=overdue_borrows_count,
            returned_borrows_count=returned_borrows_count
        )
        
        result.append(user_with_stats)
    
    return result

@router.get("/admin/{user_id}", response_model=UserWithStats)
async def get_user_details(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Lấy thông tin chi tiết của một người dùng (chỉ admin)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Người dùng không tồn tại"
        )
    
    # Đếm sách đang mượn
    active_borrows_count = db.query(func.count(Borrow.id)).filter(
        Borrow.user_id == user.id,
        Borrow.is_returned == False
    ).scalar() or 0
    
    # Đếm sách quá hạn
    overdue_borrows_count = db.query(func.count(Borrow.id)).join(BorrowOrder).filter(
        Borrow.user_id == user.id,
        Borrow.is_returned == False,
        BorrowOrder.status == "overdue"
    ).scalar() or 0
    
    # Đếm sách đã trả
    returned_borrows_count = db.query(func.count(Borrow.id)).filter(
        Borrow.user_id == user.id,
        Borrow.is_returned == True
    ).scalar() or 0
    
    user_with_stats = UserWithStats(
        email=user.email,
        full_name=user.full_name,
        phone_number=user.phone_number,
        is_active=user.is_active,
        is_admin=user.is_admin,
        active_borrows_count=active_borrows_count,
        overdue_borrows_count=overdue_borrows_count,
        returned_borrows_count=returned_borrows_count
    )
    
    return user_with_stats

@router.put("/admin/{user_id}", response_model=UserProfile)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Cập nhật thông tin của một người dùng (chỉ admin)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Người dùng không tồn tại"
        )
    
    # Kiểm tra email đã tồn tại chưa
    if user_update.email and user_update.email != user.email:
        user_exists = db.query(User).filter(User.email == user_update.email).first()
        if user_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email đã được sử dụng"
            )
        user.email = user_update.email
    
    if user_update.full_name:
        user.full_name = user_update.full_name
    
    if user_update.phone_number:
        user.phone_number = user_update.phone_number
    
    if user_update.is_active is not None:
        user.is_active = user_update.is_active
    
    db.commit()
    db.refresh(user)
    
    return user

@router.post("/admin/{user_id}/reset-password", response_model=dict)
async def reset_user_password(
    user_id: int,
    password_reset: PasswordReset,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Đặt lại mật khẩu cho một người dùng (chỉ admin)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Người dùng không tồn tại"
        )
    
    # Cập nhật mật khẩu mới
    hashed_password = get_password_hash(password_reset.new_password)
    user.password = hashed_password
    
    db.commit()
    
    # Tạo thông báo cho người dùng
    notification = Notification(
        user_id=user.id,
        title="Mật khẩu đã được đặt lại",
        message="Mật khẩu của bạn đã được quản trị viên đặt lại. Vui lòng liên hệ quản trị viên nếu bạn không yêu cầu thay đổi này.",
        type="warning"
    )
    
    db.add(notification)
    db.commit()
    
    return {"message": "Đặt lại mật khẩu thành công"}

@router.post("/admin/{user_id}/toggle-active", response_model=dict)
async def toggle_user_active_status(
    user_id: int,
    reason: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Khóa hoặc mở khóa tài khoản người dùng (chỉ admin)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Người dùng không tồn tại"
        )
    
    # Không thể khóa tài khoản admin
    if user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể khóa tài khoản quản trị viên"
        )
    
    # Đổi trạng thái tài khoản
    prev_status = user.is_active
    user.is_active = not user.is_active
    
    # Tạo thông báo cho người dùng
    if prev_status:
        title = "Tài khoản đã bị khóa"
        message = f"Tài khoản của bạn đã bị khóa. Lý do: {reason}. Vui lòng liên hệ quản trị viên để biết thêm chi tiết."
        notification_type = "danger"
        action_message = "Đã khóa tài khoản thành công"
    else:
        title = "Tài khoản đã được mở khóa"
        message = "Tài khoản của bạn đã được mở khóa và có thể sử dụng bình thường."
        notification_type = "success"
        action_message = "Đã mở khóa tài khoản thành công"
    
    notification = Notification(
        user_id=user.id,
        title=title,
        message=message,
        type=notification_type
    )
    
    db.add(notification)
    db.commit()
    
    return {"message": action_message}

@router.post("/admin/lock-overdue-accounts", response_model=dict)
async def lock_overdue_accounts(
    days_overdue: int = Body(..., embed=True), 
    notify_users: bool = Body(True, embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Khóa tài khoản người dùng có sách quá hạn
    - days_overdue: Số ngày quá hạn tối thiểu để khóa tài khoản
    - notify_users: Gửi thông báo cho người dùng
    """
    from datetime import datetime, timedelta
    from sqlalchemy import text
    
    # Tính ngày tối đa để xét quá hạn
    overdue_date = datetime.utcnow() - timedelta(days=days_overdue)
    
    # Lấy danh sách người dùng có sách quá hạn
    query = """
    SELECT DISTINCT u.id, u.username, u.full_name, u.email 
    FROM users u
    JOIN borrows b ON u.id = b.user_id
    WHERE u.is_admin = FALSE AND u.is_active = TRUE
    AND b.is_returned = FALSE AND b.due_date < :overdue_date
    """
    
    result = db.execute(text(query), {'overdue_date': overdue_date})
    users_to_lock = [dict(row) for row in result]
    
    locked_count = 0
    
    # Khóa từng tài khoản và gửi thông báo
    for user_info in users_to_lock:
        user = db.query(User).filter(User.id == user_info['id']).first()
        if not user or not user.is_active:
            continue
            
        # Lấy thông tin sách quá hạn
        overdue_borrows = db.query(Borrow).filter(
            Borrow.user_id == user.id,
            Borrow.is_returned == False,
            Borrow.due_date < overdue_date
        ).all()
        
        # Danh sách tên sách quá hạn
        overdue_book_titles = []
        for borrow in overdue_borrows:
            book = db.query(Book).filter(Book.id == borrow.book_id).first()
            if book:
                days_late = (datetime.utcnow() - borrow.due_date).days
                overdue_book_titles.append(f"{book.title} (quá hạn {days_late} ngày)")
        
        # Khóa tài khoản
        user.is_active = False
        db.commit()
        locked_count += 1
        
        # Tạo thông báo cho admin
        admin_notification = Notification(
            user_id=current_user.id,
            title=f"Đã khóa tài khoản của {user.full_name}",
            message=f"Tài khoản {user.username} ({user.full_name}) đã bị khóa tự động do có sách quá hạn trên {days_overdue} ngày.\n\nSách quá hạn: {', '.join(overdue_book_titles)}",
            type="warning"
        )
        db.add(admin_notification)
        
        # Gửi thông báo cho người dùng
        if notify_users:
            user_notification = Notification(
                user_id=user.id,
                title="Tài khoản của bạn đã bị khóa",
                message=f"Tài khoản của bạn đã bị khóa do có sách quá hạn trên {days_overdue} ngày. Vui lòng liên hệ thủ thư để được hỗ trợ.\n\nSách quá hạn: {', '.join(overdue_book_titles)}",
                type="danger"
            )
            db.add(user_notification)
        
        db.commit()
    
    return {
        "message": f"Đã khóa {locked_count} tài khoản người dùng có sách quá hạn",
        "locked_users": users_to_lock
    }

@router.get("/admin/users/overdue-report", response_model=dict)
async def get_overdue_users_report(
    min_days_overdue: int = 1,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Lấy báo cáo về người dùng có sách trả quá hạn
    """
    from datetime import datetime, timedelta
    from sqlalchemy import text
    
    # Tính ngày tối đa để xét quá hạn
    overdue_date = datetime.utcnow() - timedelta(days=min_days_overdue)
    
    # Query báo cáo
    query = """
    SELECT 
        u.id, u.username, u.full_name, u.email, u.phone_number, u.is_active,
        COUNT(DISTINCT b.id) AS overdue_books_count,
        MAX(DATEDIFF(CURRENT_DATE, b.due_date)) AS max_days_overdue
    FROM users u
    JOIN borrows b ON u.id = b.user_id
    JOIN books bk ON b.book_id = bk.id
    WHERE b.is_returned = FALSE AND b.due_date < :overdue_date
    GROUP BY u.id
    ORDER BY max_days_overdue DESC
    """
    
    result = db.execute(text(query), {'overdue_date': overdue_date})
    users_report = [dict(row) for row in result]
    
    # Thêm thông tin chi tiết sách quá hạn cho mỗi người dùng
    for user_info in users_report:
        # Lấy thông tin sách quá hạn
        overdue_borrows = db.query(Borrow).join(Book).filter(
            Borrow.user_id == user_info['id'],
            Borrow.is_returned == False,
            Borrow.due_date < overdue_date
        ).all()
        
        user_info['overdue_books'] = []
        for borrow in overdue_borrows:
            days_late = (datetime.utcnow() - borrow.due_date).days
            book_info = {
                'book_id': borrow.book_id,
                'borrow_id': borrow.id,
                'title': borrow.book.title,
                'borrow_date': borrow.borrow_date.strftime('%Y-%m-%d'),
                'due_date': borrow.due_date.strftime('%Y-%m-%d'),
                'days_overdue': days_late
            }
            user_info['overdue_books'].append(book_info)
    
    return {
        "min_days_overdue": min_days_overdue,
        "total_users": len(users_report),
        "users": users_report
    } 