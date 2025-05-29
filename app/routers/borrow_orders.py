from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.database.db import get_db
from app.database.models import BorrowOrder, Book, Borrow, User, Notification
from app.auth.auth import get_current_active_user, get_current_admin_user
from app.routers.notifications import notify_all_admins
from app.utils.notifications import create_notification, notify_user_on_order_approval

# Định nghĩa các model Pydantic
class BookItemRequest(BaseModel):
    book_id: int

class BorrowOrderCreate(BaseModel):
    book_ids: List[int]
    notes: Optional[str] = None

class BorrowOrderUpdate(BaseModel):
    status: str

class BookInOrderResponse(BaseModel):
    id: int
    title: str
    author_name: str
    cover_image: Optional[str] = None
    
    class Config:
        orm_mode = True

class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    
    class Config:
        orm_mode = True

class BorrowOrderResponse(BaseModel):
    id: int
    user_id: int
    user: UserResponse
    order_date: datetime
    due_date: datetime
    status: str
    notes: Optional[str] = None
    books: List[BookInOrderResponse]
    
    class Config:
        orm_mode = True

# Tạo router
router = APIRouter(
    prefix="/api/borrow-orders",
    tags=["borrow orders"]
)

# Tạo đơn mượn sách mới
@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_borrow_order(
    order_data: BorrowOrderCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Tạo đơn mượn sách mới (tối đa 5 cuốn sách mỗi đơn)
    """
    # Kiểm tra số lượng sách
    if len(order_data.book_ids) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phải có ít nhất 1 cuốn sách trong đơn mượn"
        )
    
    if len(order_data.book_ids) > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chỉ được mượn tối đa 5 cuốn sách mỗi đơn"
        )
    
    # Kiểm tra đơn mượn đang chờ (chỉ được phép có 1 đơn đang chờ)
    pending_order = db.query(BorrowOrder).filter(
        BorrowOrder.user_id == current_user.id,
        BorrowOrder.status == "pending"
    ).first()
    
    if pending_order:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bạn đã có đơn mượn đang chờ duyệt. Vui lòng đợi đơn được duyệt trước khi tạo đơn mới."
        )
    
    # Kiểm tra số lượng sách đang mượn
    active_borrows_count = db.query(Borrow).join(BorrowOrder).filter(
        Borrow.user_id == current_user.id,
        Borrow.is_returned == False,
        BorrowOrder.status.in_(["active", "overdue"])
    ).count()
    
    if active_borrows_count + len(order_data.book_ids) > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bạn đã mượn {active_borrows_count} cuốn sách. Tổng số sách mượn không được vượt quá 5 cuốn."
        )
    
    # Kiểm tra sách tồn tại và có sẵn để mượn
    books = []
    for book_id in order_data.book_ids:
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy sách với ID {book_id}"
            )
        
        if book.available_copies <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sách '{book.title}' đã hết, không thể mượn"
            )
        
        books.append(book)
    
    # Tạo đơn mượn
    now = datetime.utcnow()
    due_date = now + timedelta(days=14)  # Thời hạn 2 tuần
    
    new_order = BorrowOrder(
        user_id=current_user.id,
        order_date=now,
        due_date=due_date,
        status="pending",
        notes=order_data.notes
    )
    
    # Thêm sách vào đơn mượn
    new_order.books = books
    
    # Lưu vào database
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    
    # Tạo thông báo cho admin về đơn mượn mới
    book_titles = [book.title for book in books]
    book_list = ", ".join(book_titles[:3])
    if len(books) > 3:
        book_list += f" và {len(books) - 3} sách khác"
    
    notify_all_admins(
        db=db,
        title="Đơn mượn mới cần duyệt",
        message=f"Đơn mượn #{new_order.id} từ {current_user.full_name} đang chờ duyệt. Sách: {book_list}.",
        notification_type="info"
    )
    
    return {
        "message": "Đã tạo đơn mượn thành công, vui lòng đợi admin duyệt.",
        "order_id": new_order.id,
        "due_date": due_date
    }

# Lấy danh sách đơn mượn của người dùng hiện tại
@router.get("/my-orders", response_model=List[BorrowOrderResponse])
async def get_my_orders(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Lấy danh sách đơn mượn của người dùng đăng nhập
    """
    query = db.query(BorrowOrder).filter(BorrowOrder.user_id == current_user.id)
    
    if status:
        query = query.filter(BorrowOrder.status == status)
    
    orders = query.order_by(BorrowOrder.order_date.desc()).all()
    
    # Chuẩn bị phản hồi
    result = []
    for order in orders:
        # Lấy thông tin sách trong đơn
        book_responses = []
        for book in order.books:
            book_response = BookInOrderResponse(
                id=book.id,
                title=book.title,
                author_name=book.author.name,
                cover_image=book.cover_image
            )
            book_responses.append(book_response)
        
        # Tạo thông tin người dùng
        user_response = UserResponse(
            id=current_user.id,
            full_name=current_user.full_name,
            email=current_user.email
        )
        
        # Tạo phản hồi đơn mượn
        order_response = BorrowOrderResponse(
            id=order.id,
            user_id=current_user.id,
            user=user_response,
            order_date=order.order_date,
            due_date=order.due_date,
            status=order.status,
            notes=order.notes,
            books=book_responses
        )
        
        result.append(order_response)
    
    return result

# Lấy thông tin chi tiết đơn mượn
@router.get("/{order_id}", response_model=BorrowOrderResponse)
async def get_order_detail(
    order_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Lấy thông tin chi tiết đơn mượn
    """
    # Kiểm tra đơn mượn tồn tại không
    order = db.query(BorrowOrder).filter(BorrowOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy đơn mượn"
        )
    
    # Kiểm tra quyền truy cập
    if order.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền xem đơn mượn này"
        )
    
    # Lấy thông tin sách trong đơn
    book_responses = []
    for book in order.books:
        book_response = BookInOrderResponse(
            id=book.id,
            title=book.title,
            author_name=book.author.name,
            cover_image=book.cover_image
        )
        book_responses.append(book_response)
    
    # Tạo thông tin người dùng
    user = db.query(User).filter(User.id == order.user_id).first()
    user_response = UserResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email
    )
    
    # Tạo phản hồi
    return BorrowOrderResponse(
        id=order.id,
        user_id=order.user_id,
        user=user_response,
        order_date=order.order_date,
        due_date=order.due_date,
        status=order.status,
        notes=order.notes,
        books=book_responses
    )

# Hủy đơn mượn (chỉ cho đơn đang chờ duyệt)
@router.post("/{order_id}/cancel", response_model=dict)
async def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Hủy đơn mượn (chỉ cho đơn đang chờ duyệt)
    """
    # Kiểm tra đơn mượn tồn tại không
    order = db.query(BorrowOrder).filter(BorrowOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy đơn mượn"
        )
    
    # Kiểm tra quyền truy cập
    if order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền hủy đơn mượn này"
        )
    
    # Kiểm tra trạng thái đơn
    if order.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chỉ có thể hủy đơn mượn đang chờ duyệt"
        )
    
    # Cập nhật trạng thái đơn
    order.status = "cancelled"
    
    # Lưu vào database
    db.commit()
    
    return {"message": "Đã hủy đơn mượn thành công"}

# Admin API

# Lấy danh sách tất cả đơn mượn (chỉ admin)
@router.get("/admin/all", response_model=List[BorrowOrderResponse])
async def get_all_orders(
    status: Optional[str] = None,
    user_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    Lấy danh sách tất cả đơn mượn (chỉ admin)
    """
    # Tạo query cơ bản
    query = db.query(BorrowOrder)
    
    # Áp dụng bộ lọc
    if status:
        query = query.filter(BorrowOrder.status == status)
    
    if user_id:
        query = query.filter(BorrowOrder.user_id == user_id)
    
    # Tính tổng số bản ghi
    total = query.count()
    
    # Phân trang
    orders = query.order_by(BorrowOrder.order_date.desc()).offset((page - 1) * limit).limit(limit).all()
    
    # Chuẩn bị phản hồi
    result = []
    for order in orders:
        # Lấy thông tin sách trong đơn
        book_responses = []
        for book in order.books:
            book_response = BookInOrderResponse(
                id=book.id,
                title=book.title,
                author_name=book.author.name,
                cover_image=book.cover_image
            )
            book_responses.append(book_response)
        
        # Tạo thông tin người dùng
        user = db.query(User).filter(User.id == order.user_id).first()
        user_response = UserResponse(
            id=user.id,
            full_name=user.full_name,
            email=user.email
        )
        
        # Tạo phản hồi đơn mượn
        order_response = BorrowOrderResponse(
            id=order.id,
            user_id=order.user_id,
            user=user_response,
            order_date=order.order_date,
            due_date=order.due_date,
            status=order.status,
            notes=order.notes,
            books=book_responses
        )
        
        result.append(order_response)
    
    return result

# Duyệt đơn mượn (chỉ admin)
@router.post("/admin/{order_id}/approve", response_model=dict)
async def approve_borrow_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    Duyệt đơn mượn (chỉ admin)
    """
    order = db.query(BorrowOrder).filter(BorrowOrder.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy đơn mượn"
        )
    
    # Kiểm tra trạng thái đơn
    if order.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chỉ có thể duyệt đơn mượn đang ở trạng thái chờ duyệt"
        )
    
    # Kiểm tra và cập nhật số lượng sách khả dụng
    for book in order.books:
        if book.available_copies <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sách '{book.title}' đã hết, không thể mượn"
            )
        
        book.available_copies -= 1
        
        # Tạo bản ghi mượn cho từng sách
        borrow = Borrow(
            user_id=order.user_id,
            book_id=book.id,
            order_id=order.id,
            borrow_date=datetime.utcnow(),
            due_date=order.due_date,
            is_returned=False,
            status="active"
        )
        db.add(borrow)
    
    # Cập nhật trạng thái đơn
    order.status = "active"
    
    # Tạo thông báo cho người dùng về việc đơn được duyệt
    notify_user_on_order_approval(db, order)
    
    # Lưu vào database
    db.commit()
    
    return {"message": "Đã duyệt đơn mượn thành công"}

# Từ chối đơn mượn (chỉ admin)
@router.post("/admin/{order_id}/reject", response_model=dict)
async def reject_borrow_order(
    order_id: int,
    reason: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    Từ chối đơn mượn (chỉ admin)
    """
    order = db.query(BorrowOrder).filter(BorrowOrder.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy đơn mượn"
        )
    
    # Kiểm tra trạng thái đơn
    if order.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chỉ có thể từ chối đơn mượn đang ở trạng thái chờ duyệt"
        )
    
    # Cập nhật trạng thái đơn
    order.status = "rejected"
    
    # Tạo thông báo cho người dùng
    notification = Notification(
        user_id=order.user_id,
        title="Đơn mượn bị từ chối",
        message=f"Đơn mượn #{order.id} của bạn đã bị từ chối. Lý do: {reason}",
        type="danger"
    )
    db.add(notification)
    
    # Lưu vào database
    db.commit()
    
    return {"message": "Đã từ chối đơn mượn thành công"}

@router.post("/admin/{order_id}/complete", response_model=dict)
async def complete_borrow_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    Đánh dấu đơn mượn đã hoàn thành (khi người dùng đã trả tất cả sách)
    """
    # Lấy thông tin đơn mượn
    order = db.query(BorrowOrder).filter(BorrowOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy đơn mượn"
        )
    
    # Kiểm tra trạng thái đơn mượn
    if order.status not in ["active", "overdue"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Không thể hoàn thành đơn mượn có trạng thái {order.status}"
        )
    
    # Kiểm tra tất cả sách đã được trả chưa
    borrows = db.query(Borrow).filter(
        Borrow.order_id == order_id,
        Borrow.is_returned == False
    ).all()
    
    if borrows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Còn {len(borrows)} sách chưa được trả"
        )
    
    # Cập nhật trạng thái đơn mượn
    order.status = "completed"
    
    # Tạo thông báo cho người dùng
    notification = Notification(
        user_id=order.user_id,
        title="Đơn mượn đã hoàn thành",
        message=f"Đơn mượn #{order.id} đã được hoàn thành. Cảm ơn bạn đã sử dụng dịch vụ thư viện!",
        type="success"
    )
    db.add(notification)
    
    db.commit()
    
    return {"message": "Đã hoàn thành đơn mượn"}

@router.post("/admin/{order_id}/complete-with-returns", response_model=dict)
async def complete_order_with_returns(
    order_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    Đánh dấu tất cả sách trong đơn là đã trả và hoàn thành đơn mượn.
    Sử dụng khi cần đánh dấu hoàn thành nhanh chóng mà không cần xử lý từng sách.
    """
    # Lấy thông tin đơn mượn
    order = db.query(BorrowOrder).filter(BorrowOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy đơn mượn"
        )
    
    # Kiểm tra trạng thái đơn mượn
    if order.status not in ["active", "overdue"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Không thể hoàn thành đơn mượn có trạng thái {order.status}"
        )
    
    # Lấy danh sách sách chưa trả trong đơn mượn
    unreturned_borrows = db.query(Borrow).filter(
        Borrow.order_id == order_id,
        Borrow.is_returned == False
    ).all()
    
    # Số lượng sách đã đánh dấu trả
    returned_count = 0
    
    # Đánh dấu tất cả sách là đã trả
    now = datetime.utcnow()
    for borrow in unreturned_borrows:
        # Đánh dấu là đã trả
        borrow.is_returned = True
        borrow.return_date = now
        borrow.status = "returned"
        
        # Thêm ghi chú
        notes = f"Trả ngày: {now.strftime('%d/%m/%Y %H:%M')}\n"
        notes += f"Tình trạng sách: Tốt\n"
        notes += f"Ghi chú: Đánh dấu trả tự động bởi quản trị viên\n"
        
        if borrow.notes:
            notes = borrow.notes + "\n\n" + notes
        
        borrow.notes = notes
        
        # Cập nhật số lượng sách có sẵn
        book = db.query(Book).filter(Book.id == borrow.book_id).first()
        if book:
            book.available_copies += 1
            
        returned_count += 1
    
    # Cập nhật trạng thái đơn mượn
    order.status = "completed"
    
    # Tạo thông báo cho người dùng
    notification = Notification(
        user_id=order.user_id,
        title="Đơn mượn đã hoàn thành",
        message=f"Đơn mượn #{order.id} đã được hoàn thành. Tất cả {returned_count} sách đã được đánh dấu là đã trả.",
        type="success"
    )
    db.add(notification)
    
    # Lưu vào database
    db.commit()
    
    return {
        "message": "Đã hoàn thành đơn mượn và đánh dấu tất cả sách là đã trả",
        "returned_books": returned_count
    }

@router.post("/admin/handle-return", response_model=dict)
async def handle_book_return(
    borrow_id: int,
    condition_ok: bool = True,
    condition_notes: Optional[str] = None,
    late_fine: Optional[float] = 0,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """DEPRECATED: Use /admin/return/{borrow_id} instead"""
    return await handle_book_return_new(borrow_id, condition_ok, condition_notes, late_fine, db, current_user)

@router.post("/admin/return/{borrow_id}", response_model=dict)
async def handle_book_return_new(
    borrow_id: int,
    condition_ok: bool = True,
    condition_notes: Optional[str] = None,
    late_fine: Optional[float] = 0,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    Ghi nhận thông tin khi độc giả trả sách
    - borrow_id: ID của bản ghi mượn sách
    - condition_ok: Tình trạng sách có tốt không
    - condition_notes: Ghi chú về tình trạng sách
    - late_fine: Tiền phạt trả sách muộn (nếu có)
    """
    # Lấy thông tin mượn sách
    borrow = db.query(Borrow).filter(Borrow.id == borrow_id).first()
    if not borrow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông tin mượn sách"
        )
    
    # Kiểm tra sách đã được trả chưa
    if borrow.is_returned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sách này đã được trả"
        )
    
    # Lấy thông tin sách và người dùng
    book = db.query(Book).filter(Book.id == borrow.book_id).first()
    user = db.query(User).filter(User.id == borrow.user_id).first()
    
    if not book or not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông tin sách hoặc người dùng"
        )
    
    # Kiểm tra quá hạn
    now = datetime.utcnow()
    is_overdue = now > borrow.due_date
    days_overdue = 0
    
    if is_overdue:
        days_overdue = (now - borrow.due_date).days
    
    # Ghi nhận thông tin trả sách
    borrow.is_returned = True
    borrow.return_date = now
    borrow.status = "returned"
    
    # Cập nhật ghi chú
    notes = f"Trả ngày: {now.strftime('%d/%m/%Y %H:%M')}\n"
    notes += f"Tình trạng sách: {'Tốt' if condition_ok else 'Có vấn đề'}\n"
    
    if condition_notes:
        notes += f"Ghi chú tình trạng: {condition_notes}\n"
    
    if is_overdue:
        notes += f"Quá hạn: {days_overdue} ngày\n"
    
    if late_fine > 0:
        notes += f"Tiền phạt: {late_fine} đồng\n"
    
    if borrow.notes:
        notes = borrow.notes + "\n\n" + notes
    
    borrow.notes = notes
    
    # Cập nhật số lượng sách có sẵn
    book.available_copies += 1
    
    # Tạo thông báo cho người dùng
    user_notification = Notification(
        user_id=user.id,
        title="Đã ghi nhận trả sách",
        message=f"Sách '{book.title}' đã được ghi nhận trả thành công.",
        type="success"
    )
    db.add(user_notification)
    
    # Nếu quá hạn, tạo thông báo nhắc nhở
    if is_overdue:
        overdue_notification = Notification(
            user_id=user.id,
            title="Sách trả quá hạn",
            message=f"Sách '{book.title}' được trả quá hạn {days_overdue} ngày. Tiền phạt: {late_fine} đồng.",
            type="warning"
        )
        db.add(overdue_notification)
    
    # Lưu các thay đổi
    db.commit()
    
    # Kiểm tra xem tất cả sách trong đơn đã được trả hết chưa
    order = db.query(BorrowOrder).filter(BorrowOrder.id == borrow.order_id).first()
    if order:
        remaining_borrows = db.query(Borrow).filter(
            Borrow.order_id == order.id,
            Borrow.is_returned == False
        ).count()
        
        # Nếu tất cả sách đã được trả, cập nhật trạng thái đơn
        if remaining_borrows == 0:
            order.status = "completed"
            db.commit()
    
    return {
        "message": "Đã ghi nhận trả sách thành công",
        "book_title": book.title,
        "user_name": user.full_name,
        "return_date": now,
        "is_overdue": is_overdue,
        "days_overdue": days_overdue,
        "late_fine": late_fine,
        "order_completed": order and remaining_borrows == 0
    }

@router.get("/admin/borrowing-history", response_model=dict)
async def get_borrowing_history(
    user_id: Optional[int] = None,
    book_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    Xem lịch sử mượn/trả sách với các bộ lọc
    """
    query = db.query(Borrow).join(Book).join(User)
    
    # Áp dụng các bộ lọc
    if user_id:
        query = query.filter(Borrow.user_id == user_id)
    
    if book_id:
        query = query.filter(Borrow.book_id == book_id)
    
    if start_date:
        query = query.filter(Borrow.borrow_date >= start_date)
    
    if end_date:
        query = query.filter(Borrow.borrow_date <= end_date)
    
    # Tính tổng số bản ghi
    total_count = query.count()
    
    # Phân trang
    query = query.order_by(Borrow.borrow_date.desc())
    query = query.offset((page - 1) * limit).limit(limit)
    
    borrows = query.all()
    
    # Chuẩn bị dữ liệu trả về
    history_items = []
    for borrow in borrows:
        returned_status = "Đã trả" if borrow.is_returned else "Chưa trả"
        if not borrow.is_returned and borrow.due_date < datetime.utcnow():
            returned_status = f"Quá hạn ({(datetime.utcnow() - borrow.due_date).days} ngày)"
        
        history_items.append({
            "id": borrow.id,
            "user_id": borrow.user_id,
            "user_name": borrow.user.full_name,
            "book_id": borrow.book_id,
            "book_title": borrow.book.title,
            "borrow_date": borrow.borrow_date.strftime("%Y-%m-%d"),
            "due_date": borrow.due_date.strftime("%Y-%m-%d"),
            "return_date": borrow.return_date.strftime("%Y-%m-%d") if borrow.return_date else None,
            "status": borrow.status,
            "is_returned": borrow.is_returned,
            "returned_status": returned_status,
            "notes": borrow.notes
        })
    
    return {
        "total": total_count,
        "page": page,
        "limit": limit,
        "pages": (total_count + limit - 1) // limit,
        "items": history_items
    }

# Lấy thống kê đơn mượn
@router.get("/admin/stats", response_model=dict)
async def get_order_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    Lấy thống kê đơn mượn
    """
    pending_count = db.query(BorrowOrder).filter(BorrowOrder.status == "pending").count()
    active_count = db.query(BorrowOrder).filter(BorrowOrder.status == "active").count()
    overdue_count = db.query(BorrowOrder).filter(BorrowOrder.status == "overdue").count()
    completed_count = db.query(BorrowOrder).filter(BorrowOrder.status == "completed").count()
    
    return {
        "pending": pending_count,
        "active": active_count,
        "overdue": overdue_count,
        "completed": completed_count,
        "total": pending_count + active_count + overdue_count + completed_count
    }