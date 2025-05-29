from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
import os
from pathlib import Path
import shutil
from jose import JWTError, jwt

from app.database.db import get_db
from app.database.models import Book, Category, Author, Publisher, Borrow
from app.auth.auth import get_current_active_user, get_current_admin_user, get_user, SECRET_KEY, ALGORITHM

# Định nghĩa các model Pydantic
class CategoryResponse(BaseModel):
    id: int
    name: str
    icon: Optional[str] = None
    
    class Config:
        orm_mode = True

class AuthorResponse(BaseModel):
    id: int
    name: str
    
    class Config:
        orm_mode = True

class PublisherResponse(BaseModel):
    id: int
    name: str
    
    class Config:
        orm_mode = True

class BookBase(BaseModel):
    title: str
    isbn: str
    publication_year: Optional[int] = None
    pages: Optional[int] = None
    language: Optional[str] = None
    description: Optional[str] = None
    cover_image: Optional[str] = None
    total_copies: int
    available_copies: int
    author_id: int
    publisher_id: int

class BookCreate(BookBase):
    category_ids: List[int]

class BookResponse(BookBase):
    id: int
    author: AuthorResponse
    publisher: PublisherResponse
    categories: List[CategoryResponse]
    
    class Config:
        orm_mode = True

class BookSimple(BaseModel):
    id: int
    title: str
    author: AuthorResponse
    cover_image: Optional[str] = None
    available_copies: int
    
    class Config:
        orm_mode = True

class BorrowCreate(BaseModel):
    book_id: int
    notes: Optional[str] = None

class BorrowResponse(BaseModel):
    id: int
    book_id: int
    book_title: str
    borrow_date: datetime
    due_date: datetime
    return_date: Optional[datetime] = None
    is_returned: bool
    status: str
    order_id: Optional[int] = None
    
    class Config:
        orm_mode = True

# Tạo router
router = APIRouter(
    prefix="/api",
    tags=["books"],
    responses={404: {"description": "Not found"}},
)

# Lấy danh sách tất cả sách
@router.get("/books", response_model=List[BookSimple])
async def get_books(
    skip: int = 0, 
    limit: int = 100, 
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách sách có phân trang và tìm kiếm
    """
    query = db.query(Book)
    
    # Tìm kiếm theo từ khóa
    if search:
        query = query.filter(Book.title.ilike(f"%{search}%"))
    
    # Lọc theo thể loại
    if category_id:
        query = query.join(Book.categories).filter(Category.id == category_id)
    
    # Phân trang
    books = query.offset(skip).limit(limit).all()
    
    return books

# Lấy chi tiết một sách
@router.get("/books/{book_id}", response_model=BookResponse)
async def get_book(book_id: int, db: Session = Depends(get_db)):
    """
    Lấy thông tin chi tiết của một sách
    """
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy sách"
        )
    return book

# Lấy danh sách thể loại
@router.get("/categories/all", response_model=List[CategoryResponse])
async def get_categories(db: Session = Depends(get_db)):
    """
    Lấy danh sách tất cả thể loại sách
    """
    categories = db.query(Category).all()
    return categories

# Lấy sách theo thể loại
@router.get("/categories/{category_id}", response_model=List[BookSimple])
async def get_books_by_category(
    category_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách sách theo thể loại
    """
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thể loại"
        )
    
    books = db.query(Book).join(Book.categories).filter(
        Category.id == category_id
    ).offset(skip).limit(limit).all()
    
    return books

# Mượn sách (yêu cầu đăng nhập)
@router.post("/books/borrow", response_model=dict, status_code=status.HTTP_201_CREATED)
async def borrow_book(
    borrow_data: BorrowCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Mượn sách (yêu cầu đăng nhập)
    """
    # Kiểm tra sách tồn tại không
    book = db.query(Book).filter(Book.id == borrow_data.book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy sách"
        )
    
    # Kiểm tra còn sách không
    if book.available_copies <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sách đã hết, không thể mượn"
        )
    
    # Kiểm tra người dùng đã mượn sách này chưa
    existing_borrow = db.query(Borrow).filter(
        Borrow.user_id == current_user.id,
        Borrow.book_id == borrow_data.book_id,
        Borrow.is_returned == False
    ).first()
    
    if existing_borrow:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bạn đã mượn cuốn sách này rồi và chưa trả"
        )
    
    # Kiểm tra số lượng sách đang mượn
    active_borrows = db.query(Borrow).filter(
        Borrow.user_id == current_user.id,
        Borrow.is_returned == False
    ).count()
    
    if active_borrows >= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bạn đang mượn quá nhiều sách (tối đa 5 cuốn)"
        )
    
    # Tạo bản ghi mượn sách
    now = datetime.utcnow()
    due_date = now + timedelta(days=14)  # Thời hạn 2 tuần
    
    new_borrow = Borrow(
        user_id=current_user.id,
        book_id=borrow_data.book_id,
        borrow_date=now,
        due_date=due_date,
        is_returned=False,
        status="active",
        notes=borrow_data.notes
    )
    
    # Cập nhật số lượng sách khả dụng
    book.available_copies -= 1
    
    # Lưu vào database
    db.add(new_borrow)
    db.commit()
    
    return {"message": "Mượn sách thành công", "due_date": due_date}

# Trả sách (yêu cầu đăng nhập)
@router.post("/books/return/{borrow_id}", response_model=dict)
async def return_book(
    borrow_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Trả sách (yêu cầu đăng nhập)
    """
    # Kiểm tra bản ghi mượn sách tồn tại không
    borrow = db.query(Borrow).filter(Borrow.id == borrow_id).first()
    if not borrow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy bản ghi mượn sách"
        )
    
    # Kiểm tra bản ghi thuộc về người dùng hiện tại không
    if borrow.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền trả sách này"
        )
    
    # Kiểm tra sách đã được trả chưa
    if borrow.is_returned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sách này đã được trả rồi"
        )
    
    # Cập nhật bản ghi mượn sách
    borrow.is_returned = True
    borrow.return_date = datetime.utcnow()
    borrow.status = "returned"
    
    # Cập nhật số lượng sách khả dụng
    book = db.query(Book).filter(Book.id == borrow.book_id).first()
    book.available_copies += 1
    
    # Lưu vào database
    db.commit()
    
    return {"message": "Trả sách thành công"}

# Lấy danh sách sách đang mượn của người dùng hiện tại
@router.get("/books/my-borrows", response_model=List[BorrowResponse])
async def get_my_borrows(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Lấy danh sách sách đang mượn của người dùng hiện tại
    """
    borrows = db.query(Borrow).join(Book).filter(
        Borrow.user_id == current_user.id
    ).order_by(Borrow.borrow_date.desc()).all()
    
    # Chuyển đổi kết quả từ model ORM sang response model
    result = []
    for borrow in borrows:
        borrow_response = BorrowResponse(
            id=borrow.id,
            book_id=borrow.book_id,
            book_title=borrow.book.title,
            borrow_date=borrow.borrow_date,
            due_date=borrow.due_date,
            return_date=borrow.return_date,
            is_returned=borrow.is_returned,
            status=borrow.status,
            order_id=borrow.order_id
        )
        result.append(borrow_response)
    
    return result

# API thêm sách mới (chỉ admin)
@router.post("/books", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(
    book_data: BookCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    Tạo sách mới (chỉ Admin)
    """
    # Kiểm tra tác giả tồn tại không
    author = db.query(Author).filter(Author.id == book_data.author_id).first()
    if not author:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tác giả"
        )
    
    # Kiểm tra NXB tồn tại không
    publisher = db.query(Publisher).filter(Publisher.id == book_data.publisher_id).first()
    if not publisher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy nhà xuất bản"
        )
    
    # Kiểm tra thể loại tồn tại không
    for category_id in book_data.category_ids:
        category = db.query(Category).filter(Category.id == category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy thể loại với ID {category_id}"
            )
    
    # Kiểm tra ISBN đã tồn tại chưa
    existing_book = db.query(Book).filter(Book.isbn == book_data.isbn).first()
    if existing_book:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã ISBN đã tồn tại"
        )
    
    # Kiểm tra năm xuất bản không được lớn hơn năm hiện tại
    if book_data.publication_year and book_data.publication_year > datetime.now().year:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Năm xuất bản không thể lớn hơn năm hiện tại ({datetime.now().year})"
        )
    
    # Tạo book mới
    new_book = Book(
        title=book_data.title,
        isbn=book_data.isbn,
        publication_year=book_data.publication_year,
        pages=book_data.pages,
        language=book_data.language,
        description=book_data.description,
        cover_image=book_data.cover_image,
        total_copies=book_data.total_copies,
        available_copies=book_data.available_copies,
        author_id=book_data.author_id,
        publisher_id=book_data.publisher_id
    )
    
    # Thêm vào database
    db.add(new_book)
    db.commit()
    db.refresh(new_book)
    
    # Thêm thể loại cho sách
    for category_id in book_data.category_ids:
        category = db.query(Category).filter(Category.id == category_id).first()
        new_book.categories.append(category)
    
    db.commit()
    db.refresh(new_book)
    
    return new_book

@router.put("/books/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: int,
    book_data: BookCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    Cập nhật thông tin sách (chỉ Admin)
    """
    # Kiểm tra sách tồn tại không
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy sách"
        )
    
    # Kiểm tra tác giả tồn tại không
    author = db.query(Author).filter(Author.id == book_data.author_id).first()
    if not author:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tác giả"
        )
    
    # Kiểm tra NXB tồn tại không
    publisher = db.query(Publisher).filter(Publisher.id == book_data.publisher_id).first()
    if not publisher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy nhà xuất bản"
        )
    
    # Kiểm tra thể loại tồn tại không
    for category_id in book_data.category_ids:
        category = db.query(Category).filter(Category.id == category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy thể loại với ID {category_id}"
            )
    
    # Kiểm tra ISBN đã tồn tại chưa (nếu thay đổi)
    if book_data.isbn != book.isbn:
        existing_book = db.query(Book).filter(Book.isbn == book_data.isbn).first()
        if existing_book:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mã ISBN đã tồn tại"
            )
    
    # Kiểm tra năm xuất bản không được lớn hơn năm hiện tại
    if book_data.publication_year and book_data.publication_year > datetime.now().year:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Năm xuất bản không thể lớn hơn năm hiện tại ({datetime.now().year})"
        )
    
    # Cập nhật thông tin sách
    book.title = book_data.title
    book.isbn = book_data.isbn
    book.publication_year = book_data.publication_year
    book.pages = book_data.pages
    book.language = book_data.language
    book.description = book_data.description
    
    # Chỉ cập nhật cover_image nếu có giá trị mới
    if book_data.cover_image:
        book.cover_image = book_data.cover_image
    
    book.total_copies = book_data.total_copies
    book.available_copies = book_data.available_copies
    book.author_id = book_data.author_id
    book.publisher_id = book_data.publisher_id
    
    # Cập nhật thể loại
    book.categories.clear()
    for category_id in book_data.category_ids:
        category = db.query(Category).filter(Category.id == category_id).first()
        book.categories.append(category)
    
    db.commit()
    db.refresh(book)
    
    return book

@router.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    Xóa sách (chỉ Admin)
    """
    # Kiểm tra sách tồn tại không
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy sách"
        )
    
    # Kiểm tra sách có đang được mượn không
    active_borrows = db.query(Borrow).filter(
        Borrow.book_id == book_id,
        Borrow.is_returned == False
    ).first()
    
    if active_borrows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể xóa sách đang được mượn"
        )
    
    # Xóa sách
    db.delete(book)
    db.commit()
    
    return {"message": "Đã xóa sách thành công"}

# Upload ảnh bìa sách (chỉ admin)
@router.post("/books/upload/book-cover", status_code=status.HTTP_201_CREATED)
async def upload_book_cover(
    file: UploadFile = File(...),
    current_user = Depends(get_current_admin_user)
):
    """
    Upload a book cover image (Admin only)
    """
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Create upload directory if it doesn't exist
    upload_dir = Path("static/images/book_covers")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename with original extension
    file_ext = file.filename.split(".")[-1]
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_ext}"
    file_path = upload_dir / filename
    
    # Save uploaded file
    try:
        with file_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save file: {str(e)}"
        )
    finally:
        file.file.close()
    
    # Return URL path relative to static directory
    return {"url": f"/static/images/book_covers/{filename}"}

# Statistics API endpoints
@router.get("/statistics/overview")
async def get_overview_statistics(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Lấy thống kê tổng quan
    """
    # Check authentication via cookie or Bearer token
    try:
        # Try cookie first
        token = request.cookies.get("access_token")
        if token:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username:
                user = get_user(db, username)
                if not (user and user.is_admin and user.is_active):
                    raise HTTPException(status_code=401, detail="Admin access required")
        else:
            raise HTTPException(status_code=401, detail="Authentication required")
    except (JWTError, Exception):
        raise HTTPException(status_code=401, detail="Invalid authentication")
    
    from sqlalchemy import func, and_
    from app.database.models import User, BorrowOrder
    
    # Tổng số sách
    total_books = db.query(func.count(Book.id)).scalar()
    
    # Tổng số người dùng
    total_users = db.query(func.count(User.id)).filter(User.is_admin == False).scalar()
    
    # Tổng số đơn mượn
    total_orders = db.query(func.count(BorrowOrder.id)).scalar()
    
    # Số sách đang được mượn
    books_borrowed = db.query(func.count(Borrow.id)).filter(
        Borrow.return_date.is_(None)
    ).scalar()
    
    # Số sách quá hạn
    overdue_books = db.query(func.count(Borrow.id)).filter(
        and_(
            Borrow.return_date.is_(None),
            Borrow.due_date < datetime.utcnow()
        )
    ).scalar()
    
    return {
        "total_books": total_books,
        "total_users": total_users,
        "total_orders": total_orders,
        "books_borrowed": books_borrowed,
        "overdue_books": overdue_books,
        "available_books": total_books - books_borrowed if total_books and books_borrowed else total_books
    }

@router.get("/statistics/monthly-borrows")
async def get_monthly_borrow_statistics(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Thống kê mượn sách theo tháng (12 tháng gần nhất)
    """
    # Check authentication
    try:
        token = request.cookies.get("access_token")
        if token:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username:
                user = get_user(db, username)
                if not (user and user.is_admin and user.is_active):
                    raise HTTPException(status_code=401, detail="Admin access required")
        else:
            raise HTTPException(status_code=401, detail="Authentication required")
    except (JWTError, Exception):
        raise HTTPException(status_code=401, detail="Invalid authentication")
    
    from sqlalchemy import func, extract
    from app.database.models import BorrowOrder
    
    # Lấy dữ liệu 12 tháng gần nhất
    monthly_stats = db.query(
        extract('year', BorrowOrder.order_date).label('year'),
        extract('month', BorrowOrder.order_date).label('month'),
        func.count(BorrowOrder.id).label('count')
    ).filter(
        BorrowOrder.order_date >= datetime.utcnow() - timedelta(days=365)
    ).group_by(
        extract('year', BorrowOrder.order_date),
        extract('month', BorrowOrder.order_date)
    ).order_by(
        extract('year', BorrowOrder.order_date),
        extract('month', BorrowOrder.order_date)
    ).all()
    
    # Chuyển đổi dữ liệu
    data = []
    for stat in monthly_stats:
        month_name = [
            "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6",
            "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12"
        ][int(stat.month) - 1]
        
        data.append({
            "month": f"{month_name} {int(stat.year)}",
            "count": stat.count
        })
    
    return {"data": data}

@router.get("/statistics/popular-books")
async def get_popular_books_statistics(
    request: Request,
    limit: int = Query(10, description="Số lượng sách phổ biến cần lấy"),
    db: Session = Depends(get_db)
):
    """
    Thống kê sách được mượn nhiều nhất
    """
    # Check authentication
    try:
        token = request.cookies.get("access_token")
        if token:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username:
                user = get_user(db, username)
                if not (user and user.is_admin and user.is_active):
                    raise HTTPException(status_code=401, detail="Admin access required")
        else:
            raise HTTPException(status_code=401, detail="Authentication required")
    except (JWTError, Exception):
        raise HTTPException(status_code=401, detail="Invalid authentication")
    
    from sqlalchemy import func
    
    popular_books = db.query(
        Book.id,
        Book.title,
        Book.cover_image,
        func.count(Borrow.id).label('borrow_count')
    ).join(
        Borrow, Book.id == Borrow.book_id
    ).group_by(
        Book.id, Book.title, Book.cover_image
    ).order_by(
        func.count(Borrow.id).desc()
    ).limit(limit).all()
    
    data = []
    for book in popular_books:
        data.append({
            "id": book.id,
            "title": book.title,
            "cover_image": book.cover_image or "/static/images/book_default.svg",
            "borrow_count": book.borrow_count
        })
    
    return {"data": data}

@router.get("/statistics/categories")
async def get_category_statistics(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Thống kê theo danh mục sách
    """
    # Check authentication
    try:
        token = request.cookies.get("access_token")
        if token:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username:
                user = get_user(db, username)
                if not (user and user.is_admin and user.is_active):
                    raise HTTPException(status_code=401, detail="Admin access required")
        else:
            raise HTTPException(status_code=401, detail="Authentication required")
    except (JWTError, Exception):
        raise HTTPException(status_code=401, detail="Invalid authentication")
    
    from sqlalchemy import func
    from app.database.models import book_category
    
    category_stats = db.query(
        Category.name,
        func.count(book_category.c.book_id).label('book_count'),
        func.count(Borrow.id).label('borrow_count')
    ).outerjoin(
        book_category, Category.id == book_category.c.category_id
    ).outerjoin(
        Book, book_category.c.book_id == Book.id
    ).outerjoin(
        Borrow, Book.id == Borrow.book_id
    ).group_by(
        Category.id, Category.name
    ).order_by(
        func.count(Borrow.id).desc()
    ).all()
    
    data = []
    for stat in category_stats:
        data.append({
            "name": stat.name,
            "book_count": stat.book_count or 0,
            "borrow_count": stat.borrow_count or 0
        })
    
    return {"data": data}

@router.get("/statistics/user-activity")
async def get_user_activity_statistics(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Thống kê hoạt động người dùng
    """
    # Check authentication
    try:
        token = request.cookies.get("access_token")
        if token:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username:
                user = get_user(db, username)
                if not (user and user.is_admin and user.is_active):
                    raise HTTPException(status_code=401, detail="Admin access required")
        else:
            raise HTTPException(status_code=401, detail="Authentication required")
    except (JWTError, Exception):
        raise HTTPException(status_code=401, detail="Invalid authentication")
    
    from sqlalchemy import func, and_
    from app.database.models import User, BorrowOrder
    
    # Người dùng hoạt động (có mượn sách trong 30 ngày qua)
    active_users = db.query(func.count(func.distinct(BorrowOrder.user_id))).filter(
        BorrowOrder.order_date >= datetime.utcnow() - timedelta(days=30)
    ).scalar()
    
    # Người dùng mới (đăng ký trong 30 ngày qua)
    new_users = db.query(func.count(User.id)).filter(
        and_(
            User.created_at >= datetime.utcnow() - timedelta(days=30),
            User.is_admin == False
        )
    ).scalar()
    
    # Top người dùng mượn nhiều nhất
    top_users = db.query(
        User.full_name,
        func.count(BorrowOrder.id).label('order_count')
    ).join(
        BorrowOrder, User.id == BorrowOrder.user_id
    ).filter(
        User.is_admin == False
    ).group_by(
        User.id, User.full_name
    ).order_by(
        func.count(BorrowOrder.id).desc()
    ).limit(5).all()
    
    top_users_data = []
    for user in top_users:
        top_users_data.append({
            "name": user.full_name,
            "order_count": user.order_count
        })
    
    return {
        "active_users": active_users or 0,
        "new_users": new_users or 0,
        "top_users": top_users_data
    }
