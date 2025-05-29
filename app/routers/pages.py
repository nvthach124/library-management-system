from fastapi import APIRouter, Request, Depends, HTTPException, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, desc, or_, text
import os
from typing import List, Optional
from jose import JWTError, jwt
from datetime import datetime, timedelta

from app.database.db import get_db
from app.database.models import Book, Category, Author, Publisher, Borrow, BorrowOrder, User, Notification
from app.auth.auth import get_current_user, get_user, SECRET_KEY, ALGORITHM
from app.routers.users import get_current_user_borrows

# Tạo templates object
templates = Jinja2Templates(directory="templates")

# Tạo router
router = APIRouter(tags=["pages"])

async def get_user_from_request(request: Request, db: Session):
    """
    Helper function to get user from request
    """
    token = request.cookies.get("access_token")
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        
        user = get_user(db, username)
        return user
    except JWTError:
        return None

# Trang chủ
@router.get("/", response_class=HTMLResponse)
async def home_page(request: Request, db: Session = Depends(get_db)):
    """
    Trang chủ
    """
    current_user = await get_user_from_request(request, db)
    
    # # Redirect to admin dashboard if the user is an admin
    if current_user and current_user.is_admin:
        return RedirectResponse(url="/admin/dashboard", status_code=303)
    
    # Lấy danh sách sách nổi bật (20 cuốn sách mới nhất)
    recent_books = db.query(Book).order_by(Book.created_at.desc()).limit(20).all()
    
    # Lấy 8 sách mới nhất được thêm vào hệ thống
    recent_admin_books = db.query(Book).order_by(Book.created_at.desc()).limit(8).all()
    
    # Lấy danh sách thể loại và đếm số sách trong mỗi thể loại
    categories = db.query(Category).all()
    
    # Đếm số sách cho mỗi thể loại
    for category in categories:
        category.book_count = db.query(Book).join(Book.categories).filter(Category.id == category.id).count()
        
    # Kiểm tra xem người dùng đã mượn sách nào chưa
    all_books = recent_books + recent_admin_books
    unique_books = {}
    for book in all_books:
        if book.id not in unique_books:
            unique_books[book.id] = book
            book.is_borrowed_by_user = False
    
    if current_user:
        # Lấy danh sách sách đang mượn của người dùng
        borrowed_books = db.query(Borrow).filter(
            Borrow.user_id == current_user.id,
            Borrow.is_returned == False
        ).all()
        
        # Tạo danh sách ID của các sách đang mượn
        borrowed_book_ids = [borrow.book_id for borrow in borrowed_books]
        
        # Đánh dấu sách nào đang được mượn
        for book_id, book in unique_books.items():
            book.is_borrowed_by_user = book_id in borrowed_book_ids
    
    # Render template
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request, 
            "current_user": current_user,
            "books": recent_books,
            "recent_admin_books": recent_admin_books,
            "categories": categories,
            "featured_books": recent_books[:6]  # Hiển thị 6 sách nổi bật đầu tiên
        }
    )

@router.get("/books/{book_id}", response_class=HTMLResponse)
async def book_detail(request: Request, book_id: int, db: Session = Depends(get_db)):
    """
    Trang chi tiết sách
    """
    # Lấy thông tin sách
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        return RedirectResponse(url="/")
    
    # Lấy sách liên quan (cùng thể loại)
    related_books = []
    if book.categories:
        category = book.categories[0]
        related_books = db.query(Book).join(Book.categories).filter(
            Category.id == category.id,
            Book.id != book_id
        ).limit(4).all()
    
    # Kiểm tra người dùng đã đăng nhập chưa
    user = await get_user_from_request(request, db)
    user_authenticated = user is not None
    
    # Kiểm tra xem người dùng đã mượn sách này chưa
    book.is_borrowed_by_user = False
    if user:
        # Lấy thông tin mượn sách của người dùng
        borrow = db.query(Borrow).filter(
            Borrow.user_id == user.id,
            Borrow.book_id == book.id,
            Borrow.is_returned == False
        ).first()
        
        book.is_borrowed_by_user = borrow is not None
    
    return templates.TemplateResponse("detailbook.html", {
        "request": request,
        "book": book,
        "related_books": related_books,
        "user_authenticated": user_authenticated,
        "user": user,
        "current_user": user  # Add current_user for header component consistency
    })

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    """
    Trang đăng nhập
    """
    # Kiểm tra người dùng đã đăng nhập chưa
    user = await get_user_from_request(request, db)
    if user:
        return RedirectResponse(url="/")
    
    return templates.TemplateResponse("login.html", {
        "request": request
    })

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, db: Session = Depends(get_db)):
    """
    Trang đăng ký
    """
    # Kiểm tra người dùng đã đăng nhập chưa
    user = await get_user_from_request(request, db)
    if user:
        return RedirectResponse(url="/")
    
    return templates.TemplateResponse("register.html", {
        "request": request
    })

@router.get("/logout", response_class=HTMLResponse)
async def logout_page():
    """
    Đăng xuất và chuyển hướng về trang chủ
    """
    response = RedirectResponse(url="/")
    response.delete_cookie(key="access_token")
    return response

@router.get("/categories/{category_id}", response_class=HTMLResponse)
async def category_page(request: Request, category_id: int, db: Session = Depends(get_db)):
    """
    Trang danh sách sách theo thể loại
    """
    # Lấy thông tin thể loại
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        return RedirectResponse(url="/")
    
    # Lấy danh sách sách theo thể loại
    books = db.query(Book).join(Book.categories).filter(
        Category.id == category_id
    ).all()
    
    return templates.TemplateResponse("category.html", {
        "request": request,
        "category": category,
        "books": books
    })

@router.get("/search", response_class=HTMLResponse)
async def search_page(
    request: Request, 
    q: Optional[str] = None, 
    category: Optional[str] = None,
    author: Optional[str] = None,
    publisher: Optional[str] = None,
    availability: Optional[str] = None,
    sort: Optional[str] = None,
    page: int = 1,
    limit: int = 12,
    fetch_books_only: Optional[bool] = False,
    db: Session = Depends(get_db)
):
    """
    Trang tìm kiếm sách với nhiều bộ lọc
    Có thể trả về toàn bộ trang hoặc chỉ phần sách nếu fetch_books_only=True
    """
    # Get current user
    current_user = await get_user_from_request(request, db)
    
    # Basic search query
    query = db.query(Book).distinct()
    
    # Apply filters
    if q:
        search_term = f"%{q}%"
        query = query.filter(
            or_(
                Book.title.ilike(search_term),
                Book.description.ilike(search_term),
                Book.isbn.ilike(search_term),
                Author.name.ilike(search_term)
            )
        ).join(Author, Book.author_id == Author.id, isouter=True)
    
    # Handle multiple category IDs using OR logic
    if category and isinstance(category, str):
        category_ids = [int(c) for c in category.split(',')]
        if category_ids:
            category_filter = or_(*[Category.id == cat_id for cat_id in category_ids])
            query = query.join(Book.categories, isouter=True).filter(category_filter)
    
    # Handle multiple author IDs using OR logic
    if author and isinstance(author, str):
        author_ids = [int(a) for a in author.split(',')]
        if author_ids:
            author_filter = or_(*[Book.author_id == auth_id for auth_id in author_ids])
            query = query.filter(author_filter)
    
    # Handle multiple publisher IDs using OR logic
    if publisher and isinstance(publisher, str):
        publisher_ids = [int(p) for p in publisher.split(',')]
        if publisher_ids:
            publisher_filter = or_(*[Book.publisher_id == pub_id for pub_id in publisher_ids])
            query = query.filter(publisher_filter)
    
    # Availability filter
    if availability:
        if availability == 'available':
            query = query.filter(Book.available_copies > 0)
        elif availability == 'unavailable':
            query = query.filter(Book.available_copies == 0)
    
    # Apply sorting
    if sort:
        if sort == 'title-asc':
            query = query.order_by(Book.title)
        elif sort == 'title-desc':
            query = query.order_by(Book.title.desc())
        elif sort == 'newest':
            query = query.order_by(Book.created_at.desc())
        elif sort == 'oldest':
            query = query.order_by(Book.created_at.asc())
      
    else:
        # Default sorting
        query = query.order_by(Book.title)
    
    # Count total books matching the search
    total_books = query.count()
    
    # Calculate total pages
    total_pages = (total_books + limit - 1) // limit if total_books > 0 else 1
    
    # Ensure page is in valid range
    page = max(1, min(page, total_pages))
    
    # Get books for current page
    books = query.offset((page - 1) * limit).limit(limit).all()
    
    # Get categories, authors and publishers for filters
    categories = db.query(Category).order_by(Category.name).all()
    authors = db.query(Author).order_by(Author.name).all()
    publishers = db.query(Publisher).order_by(Publisher.name).all()
    
    # Count books for each filter
    for category in categories:
        category.book_count = db.query(Book).join(Book.categories).filter(Category.id == category.id).count()
    
    for author in authors:
        author.book_count = db.query(Book).filter(Book.author_id == author.id).count()
    
    for publisher in publishers:
        publisher.book_count = db.query(Book).filter(Book.publisher_id == publisher.id).count()
    
    # Mark borrowed books
    if current_user:
        borrowed_books = db.query(Borrow).filter(
            Borrow.user_id == current_user.id,
            Borrow.is_returned == False
        ).all()
        
        borrowed_book_ids = [borrow.book_id for borrow in borrowed_books]
        
        for book in books:
            book.is_borrowed_by_user = book.id in borrowed_book_ids
    
    # If no search query but we have a user, show popular books
    if not q and not category and not author and not publisher and not availability:
        # Get popular books with most borrows
        popular_books_query = db.query(
            Book, func.count(Borrow.id).label('borrow_count')
        ).outerjoin(
            Borrow
        ).group_by(
            Book.id
        ).order_by(
            desc('borrow_count'), 
            Book.created_at.desc()
        ).limit(limit)
        
        popular_books = [book for book, _ in popular_books_query.all()]
        
        if popular_books:
            books = popular_books
    
    # Helper function to build pagination URLs with existing query parameters
    def build_pagination_url(page_num):
        params = {"page": page_num}
        if q:
            params["q"] = q
        if category:
            params["category"] = category
        if author:
            params["author"] = author
        if publisher:
            params["publisher"] = publisher
        if availability:
            params["availability"] = availability
        if sort:
            params["sort"] = sort
        
        query_string = "&".join([f"{key}={value}" for key, value in params.items()])
        return f"/search?{query_string}"
    
    # Determine the selected values for the filters
    selected_categories = category.split(',') if category and isinstance(category, str) else []
    selected_authors = author.split(',') if author and isinstance(author, str) else []
    selected_publishers = publisher.split(',') if publisher and isinstance(publisher, str) else []
    
    return templates.TemplateResponse("search.html", {
        "request": request,
        "current_user": current_user,
        "query": q,
        "books": books,
        "count": total_books,
        "categories": categories,
        "authors": authors,
        "publishers": publishers,
        "selected_categories": selected_categories,
        "selected_authors": selected_authors,
        "selected_publishers": selected_publishers,
        "availability": availability,
        "sort": sort,
        "page": page,
        "total_pages": total_pages,
        "build_pagination_url": build_pagination_url
    })

@router.get("/books", response_class=HTMLResponse)
async def books_page(
    request: Request, 
    page: int = 1, 
    limit: int = 12, 
    category_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Trang hiển thị tất cả sách với phân trang
    """
    # Lấy người dùng hiện tại
    current_user = await get_user_from_request(request, db)
    
    # Tạo query cơ bản
    query = db.query(Book)
    
    # Lọc theo category nếu có
    if category_id:
        query = query.join(Book.categories).filter(Category.id == category_id)
    
    # Đếm tổng số sách
    total_books = query.count()
    
    # Tính tổng số trang
    total_pages = (total_books + limit - 1) // limit
    
    # Đảm bảo page nằm trong khoảng hợp lệ
    page = max(1, min(page, total_pages)) if total_pages > 0 else 1
    
    # Lấy sách theo trang
    books = query.order_by(Book.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    
    # Lấy danh sách thể loại cho sidebar
    categories = db.query(Category).all()
    
    # Đếm số sách cho mỗi thể loại
    for category in categories:
        category.book_count = db.query(Book).join(Book.categories).filter(Category.id == category.id).count()
        
    # Kiểm tra xem người dùng đã mượn sách nào chưa
    if current_user:
        # Lấy danh sách sách đang mượn của người dùng
        borrowed_books = db.query(Borrow).filter(
            Borrow.user_id == current_user.id,
            Borrow.is_returned == False
        ).all()
        
        # Tạo danh sách ID của các sách đang mượn
        borrowed_book_ids = [borrow.book_id for borrow in borrowed_books]
        
        # Đánh dấu sách nào đang được mượn
        for book in books:
            book.is_borrowed_by_user = book.id in borrowed_book_ids
    else:
        # Nếu không có người dùng đăng nhập, không có sách nào được mượn
        for book in books:
            book.is_borrowed_by_user = False
    
    # Render template
    return templates.TemplateResponse(
        "books.html",  # Cần tạo template này
        {
            "request": request,
            "current_user": current_user,
            "books": books,
            "categories": categories,
            "current_page": page,
            "total_pages": total_pages,
            "total_books": total_books,
            "category_id": category_id
        }
    )

@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, db: Session = Depends(get_db)):
    """
    Trang thông tin cá nhân (yêu cầu đăng nhập)
    """
    user = await get_user_from_request(request, db)
    if not user:
        return RedirectResponse(url="/login?redirect=/profile")
    
    # Lấy đơn mượn đang hoạt động và sách đang mượn
    active_orders = db.query(BorrowOrder).filter(
        BorrowOrder.user_id == user.id,
        BorrowOrder.status.in_(["approved", "active"])
    ).order_by(BorrowOrder.order_date.desc()).all()
    
    active_borrows = db.query(Borrow).join(Book).filter(
        Borrow.user_id == user.id,
        Borrow.is_returned == False
    ).order_by(Borrow.borrow_date.desc()).all()
    
    # Lấy lịch sử đơn mượn (đã hoàn thành hoặc hủy)
    order_history = db.query(BorrowOrder).filter(
        BorrowOrder.user_id == user.id,
        BorrowOrder.status.in_(["completed", "rejected", "cancelled"])
    ).order_by(BorrowOrder.order_date.desc()).all()
    
    # Lấy lịch sử mượn sách (đã trả)
    borrow_history = db.query(Borrow).join(Book).filter(
        Borrow.user_id == user.id,
        Borrow.is_returned == True
    ).order_by(Borrow.return_date.desc()).all()
    
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": user,
        "current_user": user,  # Add current_user for header component consistency
        "active_orders": active_orders,
        "active_borrows": active_borrows,
        "order_history": order_history,
        "borrow_history": borrow_history
    })

# Admin Pages
@router.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    """
    Trang tổng quan admin
    """
    current_user = await get_user_from_request(request, db)
    
    # Kiểm tra quyền admin
    if not current_user or not current_user.is_admin:
        return RedirectResponse(url="/login?next=/admin/dashboard", status_code=303)
    
    # Tính toán các thống kê
    total_books = db.query(func.count(Book.id)).scalar()
    total_users = db.query(func.count(User.id)).scalar()
    pending_orders = db.query(func.count(BorrowOrder.id)).filter(BorrowOrder.status == "pending").scalar()
    overdue_orders = db.query(func.count(BorrowOrder.id)).filter(BorrowOrder.status == "overdue").scalar()
    
    # Lấy các đơn mượn gần đây
    recent_orders = db.query(BorrowOrder).order_by(BorrowOrder.order_date.desc()).limit(5).all()
    
    # Lấy danh sách sách được mượn nhiều nhất
    popular_books_query = db.query(
        Book,
        func.count(Borrow.id).label('borrow_count')
    ).join(Borrow).group_by(Book.id).order_by(desc('borrow_count')).limit(5).all()
    
    popular_books = []
    for book, count in popular_books_query:
        book.borrow_count = count
        popular_books.append(book)
    
    # Tạo dữ liệu hoạt động gần đây (ví dụ)
    recent_activities = []
    
    # Hoạt động đơn mượn
    recent_order_activities = db.query(BorrowOrder).order_by(BorrowOrder.order_date.desc()).limit(3).all()
    for order in recent_order_activities:
        activity_type = "primary"
        icon = "fa-clipboard-list"
        title = f"Đơn mượn mới #{order.id}"
        subtitle = f"Người dùng: {order.user.full_name}"
        
        if order.status == "pending":
            activity_type = "warning"
            title = f"Đơn mượn chờ duyệt #{order.id}"
        elif order.status == "overdue":
            activity_type = "danger"
            title = f"Đơn mượn quá hạn #{order.id}"
        
        recent_activities.append({
            "type": activity_type,
            "icon": icon,
            "title": title,
            "subtitle": subtitle,
            "time": order.order_date.strftime("%d/%m/%Y %H:%M")
        })
    
    # Hoạt động người dùng mới
    recent_users = db.query(User).order_by(User.created_at.desc()).limit(2).all()
    for user in recent_users:
        recent_activities.append({
            "type": "success",
            "icon": "fa-user",
            "title": "Người dùng mới đăng ký",
            "subtitle": user.full_name,
            "time": user.created_at.strftime("%d/%m/%Y %H:%M")
        })
    
    # Sắp xếp lại các hoạt động theo thời gian
    recent_activities = sorted(recent_activities, key=lambda x: datetime.strptime(x["time"], "%d/%m/%Y %H:%M"), reverse=True)[:5]
    
    # Render template
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "stats": {
                "total_books": total_books,
                "total_users": total_users,
                "pending_orders": pending_orders,
                "overdue_orders": overdue_orders
            },
            "recent_orders": recent_orders,
            "popular_books": popular_books,
            "recent_activities": recent_activities
        }
    )

@router.get("/admin/books", response_class=HTMLResponse)
async def admin_books(
    request: Request, 
    search: Optional[str] = None,
    category: Optional[str] = None,
    author: Optional[str] = None,
    publisher: Optional[str] = None,
    year: Optional[str] = None,
    availability: Optional[str] = None,
    page: int = 1,
    db: Session = Depends(get_db)
):
    """
    Trang quản lý sách admin với tìm kiếm nâng cao
    """
    current_user = await get_user_from_request(request, db)
    
    # Kiểm tra quyền admin
    if not current_user or not current_user.is_admin:
        return RedirectResponse(url="/login?next=/admin/books", status_code=303)
    
    # Số lượng sách mỗi trang
    items_per_page = 10
    
    # Tạo query cơ bản
    query = db.query(Book)
    
    # Áp dụng bộ lọc nếu có
    if search:
        query = query.filter(
            or_(
                Book.title.ilike(f"%{search}%"),
                Book.isbn.ilike(f"%{search}%"),
                Book.description.ilike(f"%{search}%")
            )
        )
    
    if category and category.strip():
        try:
            category_id = int(category)
            query = query.join(Book.categories).filter(Category.id == category_id)
        except ValueError:
            # Handle invalid category ID
            pass
    
    if author and author.strip():
        try:
            author_id = int(author)
            query = query.filter(Book.author_id == author_id)
        except ValueError:
            # Handle invalid author ID
            pass
    
    if publisher and publisher.strip():
        try:
            publisher_id = int(publisher)
            query = query.filter(Book.publisher_id == publisher_id)
        except ValueError:
            # Handle invalid publisher ID
            pass
    
    if year and year.strip():
        try:
            year_value = int(year)
            query = query.filter(Book.publication_year == year_value)
        except ValueError:
            # Handle invalid year
            pass
    
    if availability == 'available':
        query = query.filter(Book.available_copies > 0)
    elif availability == 'unavailable':
        query = query.filter(Book.available_copies == 0)
    
    # Tính tổng số sách và số trang
    total_books = query.count()
    total_pages = (total_books + items_per_page - 1) // items_per_page
    
    # Ensure page is within valid range
    page = max(1, min(page, total_pages)) if total_pages > 0 else 1
    
    # Phân trang
    books = query.order_by(Book.created_at.desc()).offset((page - 1) * items_per_page).limit(items_per_page).all()
    
    # Lấy danh sách thể loại, tác giả, nhà xuất bản cho bộ lọc
    categories = db.query(Category).order_by(Category.name).all()
    authors = db.query(Author).order_by(Author.name).all()
    publishers = db.query(Publisher).order_by(Publisher.name).all()
    
    # Lấy các năm xuất bản duy nhất
    years_query = db.query(Book.publication_year).filter(Book.publication_year != None).distinct().order_by(Book.publication_year.desc())
    years = [year[0] for year in years_query.all()]
    
    # Render template
    return templates.TemplateResponse(
        "admin/books.html",
        {
            "request": request,
            "current_user": current_user,
            "books": books,
            "categories": categories,
            "authors": authors,
            "publishers": publishers,
            "years": years,
            "search": search,
            "category_id": int(category) if category and category.strip() and category.isdigit() else None,
            "author_id": int(author) if author and author.strip() and author.isdigit() else None,
            "publisher_id": int(publisher) if publisher and publisher.strip() and publisher.isdigit() else None,
            "selected_year": int(year) if year and year.strip() and year.isdigit() else None,
            "availability": availability,
            "page": page,
            "total_pages": total_pages,
            "total_books": total_books
        }
    )

@router.get("/admin/books/create", response_class=HTMLResponse)
async def admin_create_book(request: Request, db: Session = Depends(get_db)):
    """
    Trang tạo sách mới
    """
    current_user = await get_user_from_request(request, db)
    
    # Kiểm tra quyền admin
    if not current_user or not current_user.is_admin:
        return RedirectResponse(url="/login?next=/admin/books/create", status_code=303)
    
    # Lấy danh sách thể loại, tác giả, nhà xuất bản
    categories = db.query(Category).all()
    authors = db.query(Author).all()
    publishers = db.query(Publisher).all()
    
    # Render template
    return templates.TemplateResponse(
        "admin/book_form.html",
        {
            "request": request,
            "current_user": current_user,
            "categories": categories,
            "authors": authors,
            "publishers": publishers,
            "book": None,  # None indicates this is a create operation
            "action": "create"
        }
    )

@router.get("/admin/books/{book_id}/edit", response_class=HTMLResponse)
async def admin_edit_book(book_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Trang chỉnh sửa sách
    """
    current_user = await get_user_from_request(request, db)
    
    # Kiểm tra quyền admin
    if not current_user or not current_user.is_admin:
        return RedirectResponse(url="/login?next=/admin/books/{book_id}/edit", status_code=303)
    
    # Lấy thông tin sách
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Không tìm thấy sách")
    
    # Lấy danh sách thể loại, tác giả, nhà xuất bản
    categories = db.query(Category).all()
    authors = db.query(Author).all()
    publishers = db.query(Publisher).all()
    
    # Render template
    return templates.TemplateResponse(
        "admin/book_form.html",
        {
            "request": request,
            "current_user": current_user,
            "book": book,
            "categories": categories,
            "authors": authors,
            "publishers": publishers,
            "action": "edit"
        }
    )

@router.get("/admin/users", response_class=HTMLResponse)
async def admin_users(
    request: Request, 
    search: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    db: Session = Depends(get_db)
):
    """
    Trang quản lý người dùng admin
    """
    current_user = await get_user_from_request(request, db)
    
    # Kiểm tra quyền admin
    if not current_user or not current_user.is_admin:
        return RedirectResponse(url="/login?next=/admin/users", status_code=303)
    
    # Số lượng người dùng mỗi trang
    items_per_page = 10
    
    # Tạo query cơ bản
    query = db.query(User)
    
    # Áp dụng bộ lọc nếu có
    if search:
        query = query.filter(
            (User.full_name.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%")) |
            (User.username.ilike(f"%{search}%"))
        )
    
    if status == "active":
        query = query.filter(User.is_active == True)
    elif status == "inactive":
        query = query.filter(User.is_active == False)
    
    # Tính tổng số người dùng và số trang
    total_users = query.count()
    total_pages = (total_users + items_per_page - 1) // items_per_page
    
    # Ensure page is within valid range
    page = max(1, min(page, total_pages)) if total_pages > 0 else 1
    
    # Phân trang
    users = query.order_by(User.created_at.desc()).offset((page - 1) * items_per_page).limit(items_per_page).all()
    
    # Render template
    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "current_user": current_user,
            "users": users,
            "search": search,
            "status": status,
            "page": page,
            "total_pages": total_pages,
            "total_users": total_users
        }
    )

@router.get("/admin/users/{user_id}", response_class=HTMLResponse)
async def admin_user_detail(user_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Trang chi tiết người dùng
    """
    current_user = await get_user_from_request(request, db)
    
    # Kiểm tra quyền admin
    if not current_user or not current_user.is_admin:
        return RedirectResponse(url="/login?next=/admin/users/{user_id}", status_code=303)
    
    # Lấy thông tin người dùng
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
    
    # Lấy thông tin mượn sách của người dùng
    borrow_orders = db.query(BorrowOrder).filter(BorrowOrder.user_id == user_id).order_by(BorrowOrder.order_date.desc()).all()
    
    # Render template
    return templates.TemplateResponse(
        "admin/user_detail.html",
        {
            "request": request,
            "current_user": current_user,
            "user": user,
            "borrow_orders": borrow_orders
        }
    )

@router.get("/admin/orders", response_class=HTMLResponse)
async def admin_orders(
    request: Request, 
    status: Optional[str] = None,
    search: Optional[str] = None,
    date_range: Optional[str] = None,
    return_status: Optional[str] = None,
    book_count: Optional[str] = None,
    page: int = 1,
    db: Session = Depends(get_db)
):
    """
    Trang quản lý đơn mượn admin với tìm kiếm nâng cao
    """
    current_user = await get_user_from_request(request, db)
    
    # Kiểm tra quyền admin
    if not current_user or not current_user.is_admin:
        return RedirectResponse(url="/login?next=/admin/orders", status_code=303)
    
    # Số lượng đơn mượn mỗi trang
    items_per_page = 10
    
    # Tạo query cơ bản
    query = db.query(BorrowOrder).join(User).outerjoin(Borrow, BorrowOrder.id == Borrow.order_id)
    
    # Áp dụng bộ lọc nếu có
    if search:
        # Tìm theo tên, email, hoặc ID đơn
        try:
            order_id = int(search)
            has_order_id = True
        except ValueError:
            has_order_id = False
        
        if has_order_id:
            query = query.filter(
                (BorrowOrder.id == order_id) |
                (User.full_name.ilike(f"%{search}%")) |
                (User.email.ilike(f"%{search}%"))
            )
        else:
            query = query.filter(
                (User.full_name.ilike(f"%{search}%")) |
                (User.email.ilike(f"%{search}%"))
            )
    
    if status:
        query = query.filter(BorrowOrder.status == status)
    
    # Lọc theo khoảng thời gian
    now = datetime.now()
    if date_range:
        if date_range == 'today':
            today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            query = query.filter(BorrowOrder.order_date >= today)
        elif date_range == 'yesterday':
            yesterday = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            query = query.filter(BorrowOrder.order_date >= yesterday, BorrowOrder.order_date < today)
        elif date_range == 'last7days':
            last_week = now - timedelta(days=7)
            query = query.filter(BorrowOrder.order_date >= last_week)
        elif date_range == 'last30days':
            last_month = now - timedelta(days=30)
            query = query.filter(BorrowOrder.order_date >= last_month)
        elif date_range == 'thismonth':
            start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            query = query.filter(BorrowOrder.order_date >= start_of_month)
        elif date_range == 'lastmonth':
            this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if this_month.month == 1:
                last_month = this_month.replace(year=this_month.year-1, month=12)
            else:
                last_month = this_month.replace(month=this_month.month-1)
            query = query.filter(BorrowOrder.order_date >= last_month, BorrowOrder.order_date < this_month)
    
    # Lọc theo trạng thái trả sách
    if return_status:
        # Đây là phức tạp hơn vì cần kiểm tra các bản ghi mượn
        # Lưu query gốc để sau đó áp dụng
        original_query = query
        order_ids = []
        
        # Lấy tất cả đơn mượn có trạng thái active hoặc overdue
        active_orders = original_query.filter(BorrowOrder.status.in_(["active", "overdue"])).all()
        
        for order in active_orders:
            borrows = db.query(Borrow).filter(Borrow.order_id == order.id).all()
            total_borrows = len(borrows)
            returned_borrows = len([b for b in borrows if b.is_returned])
            
            if return_status == 'returned' and returned_borrows == total_borrows and total_borrows > 0:
                order_ids.append(order.id)
            elif return_status == 'partial' and returned_borrows > 0 and returned_borrows < total_borrows:
                order_ids.append(order.id)
            elif return_status == 'not_returned' and returned_borrows == 0:
                order_ids.append(order.id)
        
        if order_ids:
            query = original_query.filter(BorrowOrder.id.in_(order_ids))
        else:
            # No matches for the filter, return empty result
            query = original_query.filter(BorrowOrder.id == -1)  # Force empty result
    
    # Lọc theo số lượng sách
    if book_count:
        # Cần lọc theo số sách trong từng đơn
        original_query = query
        order_ids = []
        
        # Lấy tất cả đơn mượn từ query ban đầu
        all_orders = original_query.all()
        
        for order in all_orders:
            num_books = len(order.books)
            
            if book_count == '1' and num_books == 1:
                order_ids.append(order.id)
            elif book_count == '2-3' and (num_books == 2 or num_books == 3):
                order_ids.append(order.id)
            elif book_count == '4-5' and (num_books == 4 or num_books == 5):
                order_ids.append(order.id)
        
        if order_ids:
            query = original_query.filter(BorrowOrder.id.in_(order_ids))
        else:
            # No matches for the filter, return empty result
            query = original_query.filter(BorrowOrder.id == -1)  # Force empty result
    
    # Nhóm lại kết quả để tránh duplicate
    query = query.group_by(BorrowOrder.id)
    
    # Tính tổng số đơn mượn và số trang
    total_orders = query.count()
    total_pages = (total_orders + items_per_page - 1) // items_per_page
    
    # Ensure page is within valid range
    page = max(1, min(page, total_pages)) if total_pages > 0 else 1
    
    # Phân trang
    orders = query.order_by(BorrowOrder.order_date.desc()).offset((page - 1) * items_per_page).limit(items_per_page).all()
    
    # Tải thông tin mượn sách cho mỗi đơn
    for order in orders:
        order.borrows = db.query(Borrow).filter(Borrow.order_id == order.id).all()
    
    # Render template
    return templates.TemplateResponse(
        "admin/orders.html",
        {
            "request": request,
            "current_user": current_user,
            "orders": orders,
            "search": search,
            "status": status,
            "date_range": date_range,
            "return_status": return_status,
            "book_count": book_count,
            "page": page,
            "total_pages": total_pages,
            "total_orders": total_orders,
            "now": datetime.now()
        }
    )

@router.get("/admin/orders/{order_id}", response_class=HTMLResponse)
async def admin_order_detail(order_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Trang chi tiết đơn mượn (admin)
    """
    # Kiểm tra quyền admin
    user = await get_user_from_request(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login?redirect=/admin/orders/" + str(order_id))
    
    # Lấy thông tin đơn mượn
    order = db.query(BorrowOrder).filter(BorrowOrder.id == order_id).first()
    if not order:
        return RedirectResponse(url="/admin/orders")
    
    # Lấy thông tin người dùng
    borrower = db.query(User).filter(User.id == order.user_id).first()
    
    # Lấy thông tin chi tiết mượn sách
    borrows = db.query(Borrow).filter(Borrow.order_id == order_id).all()
    
    # Add current datetime for calculating days remaining
    from datetime import datetime
    
    return templates.TemplateResponse("admin/order_detail.html", {
        "request": request,
        "active_page": "orders",
        "current_user": user,
        "order": order,
        "borrower": borrower,
        "borrows": borrows,
        "now": datetime.now()
    })

@router.get("/admin/book-returns", response_class=HTMLResponse)
async def admin_book_returns(request: Request, db: Session = Depends(get_db)):
    """
    Trang quản lý trả sách (admin)
    """
    # Kiểm tra quyền admin
    user = await get_user_from_request(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login?redirect=/admin/book-returns")
    
    # Lấy thông báo thành công nếu có
    success_message = request.query_params.get("success")
    
    return templates.TemplateResponse("admin/book_return.html", {
        "request": request,
        "active_page": "book_returns",
        "current_user": user,
        "success_message": success_message
    })

@router.get("/admin/overdue-reports", response_class=HTMLResponse)
async def admin_overdue_reports(request: Request, db: Session = Depends(get_db)):
    """
    Trang báo cáo người dùng quá hạn (admin)
    """
    # Kiểm tra quyền admin
    user = await get_user_from_request(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login?redirect=/admin/overdue-reports")
    
    # Lấy thống kê người dùng quá hạn
    query = """
    SELECT 
        u.full_name,
        u.username,
        u.email,
        u.phone_number,
        u.is_active,
        COUNT(DISTINCT b.id) AS overdue_books_count,
        MAX(DATEDIFF(CURRENT_DATE, b.due_date)) AS max_days_overdue
    FROM users u
    JOIN borrows b ON u.id = b.user_id
    WHERE b.is_returned = FALSE AND b.due_date < CURRENT_DATE
    GROUP BY u.id
    ORDER BY max_days_overdue DESC
    LIMIT 10
    """
    
    from sqlalchemy import text
    result = db.execute(text(query))
    overdue_users = [dict(row) for row in result]
    
    # Lấy thống kê tổng quan
    total_overdue = db.query(Borrow).filter(
        Borrow.is_returned == False,
        Borrow.due_date < datetime.utcnow()
    ).count()
    
    users_with_overdue = db.query(User.id).join(Borrow).filter(
        Borrow.is_returned == False,
        Borrow.due_date < datetime.utcnow()
    ).distinct().count()
    
    return templates.TemplateResponse("admin/overdue_reports.html", {
        "request": request,
        "active_page": "overdue_reports",
        "current_user": user,
        "overdue_users": overdue_users,
        "total_overdue": total_overdue,
        "users_with_overdue": users_with_overdue
    })

@router.get("/admin/reports", response_class=HTMLResponse)
async def admin_reports_page(request: Request, db: Session = Depends(get_db)):
    """
    Trang báo cáo thống kê admin
    """
    current_user = await get_user_from_request(request, db)
    
    # Kiểm tra quyền admin
    if not current_user or not current_user.is_admin:
        return RedirectResponse(url="/login?redirect=/admin/reports")
    
    # Đếm số thông báo chưa đọc
    unread_notifications = db.query(func.count(Notification.id)).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).scalar()
    
    return templates.TemplateResponse("admin/reports.html", {
        "request": request,
        "current_user": current_user,
        "active_page": "reports",
        "unread_notifications": unread_notifications
    })

@router.get("/my-borrows", response_class=HTMLResponse)
async def my_borrows_page(request: Request, db: Session = Depends(get_db)):
    """
    Trang quản lý mượn sách của người dùng
    """
    current_user = await get_user_from_request(request, db)
    
    # Nếu chưa đăng nhập, chuyển hướng đến trang đăng nhập
    if not current_user:
        return RedirectResponse(url="/login?next=/my-borrows", status_code=303)
    
    # Lấy thông tin đơn mượn của người dùng
    result = await get_current_user_borrows(db=db, current_user=current_user)
    
    # Đếm số thông báo chưa đọc
    unread_notifications = db.query(func.count(Notification.id)).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).scalar()
    
    # Render template
    return templates.TemplateResponse(
        "my-borrows.html",
        {
            "request": request,
            "current_user": current_user,
            "stats": result["statistics"],
            "orders": result["orders"],
            "unread_notifications": unread_notifications,
            "now": datetime.utcnow()
        }
    )

@router.get("/borrow", response_class=HTMLResponse)
async def borrow_page(request: Request, db: Session = Depends(get_db)):
    """
    Trang mượn sách
    """
    current_user = await get_user_from_request(request, db)
    
    # Nếu chưa đăng nhập, chuyển hướng đến trang đăng nhập
    if not current_user:
        return RedirectResponse(url="/login?next=/borrow", status_code=303)
    
    # Kiểm tra số lượng đơn đang chờ duyệt
    pending_orders = db.query(func.count(BorrowOrder.id)).filter(
        BorrowOrder.user_id == current_user.id,
        BorrowOrder.status == "pending"
    ).scalar()
    
    # Kiểm tra số lượng đơn đang mượn
    active_orders = db.query(func.count(BorrowOrder.id)).filter(
        BorrowOrder.user_id == current_user.id,
        BorrowOrder.status.in_(["approved", "active"])
    ).scalar()
    
    # Lấy danh sách sách có thể mượn
    available_books = db.query(Book).filter(Book.available_copies > 0).all()
    
    # Lấy danh sách thể loại cho bộ lọc
    categories = db.query(Category).all()
    
    # Render template
    return templates.TemplateResponse(
        "borrow.html",
        {
            "request": request,
            "current_user": current_user,
            "books": available_books,
            "categories": categories,
            "pending_orders": pending_orders,
            "active_orders": active_orders,
            "can_create_order": pending_orders < 2 and active_orders < 3
        }
    )

@router.get("/admin/categories", response_class=HTMLResponse)
async def admin_categories(request: Request, db: Session = Depends(get_db)):
    """
    Trang quản lý thể loại sách (admin)
    """
    user = await get_user_from_request(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login")
    
    # Import book_category association table
    from app.database.models import book_category
    
    # Lấy categories cùng với số lượng sách
    categories_with_count = db.query(
        Category,
        func.count(book_category.c.book_id).label('book_count')
    ).outerjoin(book_category).group_by(Category.id).all()
    
    # Tạo danh sách categories với thuộc tính book_count
    categories = []
    for category, book_count in categories_with_count:
        category.book_count = book_count
        categories.append(category)
    
    total_categories = len(categories)
    return templates.TemplateResponse(
        "admin/categories.html",
        {
            "request": request,
            "current_user": user,
            "categories": categories,
            "total_categories": total_categories,
            "page": 1,
            "total_pages": 1,
            "search": ""
        }
    )

@router.get("/admin/authors", response_class=HTMLResponse)  
async def admin_authors(request: Request, db: Session = Depends(get_db)):
    """
    Trang quản lý tác giả (admin)
    """
    user = await get_user_from_request(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login")
    
    # Lấy authors cùng với số lượng sách
    authors_with_count = db.query(
        Author,
        func.count(Book.id).label('book_count')
    ).outerjoin(Book).group_by(Author.id).all()
    
    # Tạo danh sách authors với thuộc tính book_count
    authors = []
    for author, book_count in authors_with_count:
        author.book_count = book_count
        authors.append(author)
    
    total_authors = len(authors)
    return templates.TemplateResponse(
        "admin/authors.html",
        {
            "request": request,
            "current_user": user,
            "authors": authors,
            "total_authors": total_authors,
            "page": 1,
            "total_pages": 1,
            "search": ""
        }
    )

@router.get("/admin/publishers", response_class=HTMLResponse)
async def admin_publishers(request: Request, db: Session = Depends(get_db)):
    """
    Trang quản lý nhà xuất bản (admin)
    """
    user = await get_user_from_request(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login")
    
    # Lấy publishers cùng với số lượng sách
    publishers_with_count = db.query(
        Publisher,
        func.count(Book.id).label('book_count')
    ).outerjoin(Book).group_by(Publisher.id).all()
    
    # Tạo danh sách publishers với thuộc tính book_count
    publishers = []
    for publisher, book_count in publishers_with_count:
        publisher.book_count = book_count
        publishers.append(publisher)
    
    total_publishers = len(publishers)
    return templates.TemplateResponse(
        "admin/publishers.html",
        {
            "request": request,
            "current_user": user,
            "publishers": publishers,
            "total_publishers": total_publishers,
            "page": 1,
            "total_pages": 1,
            "search": ""
        }
    )

# Trang thông báo
@router.get("/notifications", response_class=HTMLResponse)
async def notifications_page(request: Request, db: Session = Depends(get_db)):
    """
    Trang thông báo của người dùng
    """
    current_user = await get_user_from_request(request, db)
    
    if not current_user:
        return RedirectResponse(url="/login")
    
    # Lấy danh sách thông báo
    notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_hidden == False
    ).order_by(Notification.created_at.desc()).all()
    
    # Lấy thống kê thông báo
    total_notifications = len(notifications)
    
    unread_notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
        Notification.is_hidden == False
    ).count()
    
    return templates.TemplateResponse(
        "notifications.html",
        {
            "request": request,
            "current_user": current_user,
            "notifications": notifications,
            "total_notifications": total_notifications,
            "unread_notifications": unread_notifications
        }
    )

@router.get("/admin/notifications", response_class=HTMLResponse)
async def admin_notifications(
    request: Request, 
    search: Optional[str] = None,
    notification_type: Optional[str] = None,
    status: Optional[str] = None,
    user_id: Optional[int] = None,
    page: int = 1,
    db: Session = Depends(get_db)
):
    """
    Trang quản lý thông báo admin
    """
    current_user = await get_user_from_request(request, db)
    
    # Kiểm tra quyền admin
    if not current_user or not current_user.is_admin:
        return RedirectResponse(url="/login?next=/admin/notifications", status_code=303)
    
    # Số lượng thông báo mỗi trang
    items_per_page = 20
    
    # Tạo query cơ bản
    query = db.query(Notification).join(User, Notification.user_id == User.id)
    
    # Áp dụng bộ lọc nếu có
    if search:
        query = query.filter(
            (Notification.title.ilike(f"%{search}%")) |
            (Notification.message.ilike(f"%{search}%")) |
            (User.full_name.ilike(f"%{search}%")) |
            (User.username.ilike(f"%{search}%"))
        )
    
    if notification_type:
        query = query.filter(Notification.type == notification_type)
    
    if status == "read":
        query = query.filter(Notification.is_read == True)
    elif status == "unread":
        query = query.filter(Notification.is_read == False)
    elif status == "hidden":
        query = query.filter(Notification.is_hidden == True)
    else:
        # Mặc định chỉ hiển thị thông báo không ẩn
        query = query.filter(Notification.is_hidden == False)
    
    if user_id:
        query = query.filter(Notification.user_id == user_id)
    
    # Tính tổng số thông báo và số trang
    total_notifications = query.count()
    total_pages = (total_notifications + items_per_page - 1) // items_per_page
    
    # Ensure page is within valid range
    page = max(1, min(page, total_pages)) if total_pages > 0 else 1
    
    # Phân trang
    notifications = query.order_by(Notification.created_at.desc()).offset((page - 1) * items_per_page).limit(items_per_page).all()
    
    # Lấy thống kê
    total_count = db.query(func.count(Notification.id)).scalar()
    unread_count = db.query(func.count(Notification.id)).filter(Notification.is_read == False).scalar()
    hidden_count = db.query(func.count(Notification.id)).filter(Notification.is_hidden == True).scalar()
    
    # Lấy danh sách người dùng cho bộ lọc
    users = db.query(User).order_by(User.full_name).all()
    
    # Render template
    return templates.TemplateResponse(
        "admin/notifications.html",
        {
            "request": request,
            "current_user": current_user,
            "notifications": notifications,
            "users": users,
            "search": search,
            "notification_type": notification_type,
            "status": status,
            "selected_user_id": user_id,
            "page": page,
            "total_pages": total_pages,
            "total_notifications": total_notifications,
            "stats": {
                "total_count": total_count,
                "unread_count": unread_count,
                "hidden_count": hidden_count
            }
        }
    )

