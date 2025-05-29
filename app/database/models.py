from sqlalchemy import Column, Integer, String, ForeignKey, Date, Text, Boolean, DateTime, Table
from sqlalchemy.orm import relationship
from datetime import datetime
from .db import Base

# Bảng liên kết nhiều-nhiều giữa sách và thể loại
book_category = Table(
    'book_category',
    Base.metadata,
    Column('book_id', Integer, ForeignKey('books.id'), primary_key=True),
    Column('category_id', Integer, ForeignKey('categories.id'), primary_key=True)
)

# Bảng liên kết nhiều-nhiều giữa đơn mượn và sách
borrow_order_item = Table(
    'borrow_order_items',
    Base.metadata,
    Column('order_id', Integer, ForeignKey('borrow_orders.id'), primary_key=True),
    Column('book_id', Integer, ForeignKey('books.id'), primary_key=True)
)

class User(Base):
    """
    Model cho người dùng
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    phone_number = Column(String(20))
    address = Column(String(200))
    username = Column(String(50), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)  # Trạng thái tài khoản (bị khóa hay không)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    borrows = relationship("Borrow", back_populates="user")
    borrow_orders = relationship("BorrowOrder", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    
    def __repr__(self):
        return f"<User {self.username}>"

class Category(Base):
    """
    Model cho thể loại sách
    """
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    
    # Relationship
    books = relationship("Book", secondary=book_category, back_populates="categories")
    
    def __repr__(self):
        return f"<Category {self.name}>"

class Author(Base):
    """
    Model cho tác giả
    """
    __tablename__ = "authors"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    biography = Column(Text)
    
    # Relationship
    books = relationship("Book", back_populates="author")
    
    def __repr__(self):
        return f"<Author {self.name}>"

class Publisher(Base):
    """
    Model cho nhà xuất bản
    """
    __tablename__ = "publishers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    address = Column(String(200))
    phone = Column(String(20))
    email = Column(String(100))
    
    # Relationship
    books = relationship("Book", back_populates="publisher")
    
    def __repr__(self):
        return f"<Publisher {self.name}>"

class Book(Base):
    """
    Model cho sách
    """
    __tablename__ = "books"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    isbn = Column(String(20), unique=True, index=True)
    publication_year = Column(Integer)
    pages = Column(Integer)
    language = Column(String(50))
    description = Column(Text)
    cover_image = Column(String(255))
    total_copies = Column(Integer, default=1)
    available_copies = Column(Integer, default=1)
    author_id = Column(Integer, ForeignKey("authors.id"))
    publisher_id = Column(Integer, ForeignKey("publishers.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    author = relationship("Author", back_populates="books")
    publisher = relationship("Publisher", back_populates="books")
    categories = relationship("Category", secondary=book_category, back_populates="books")
    borrows = relationship("Borrow", back_populates="book")
    borrow_orders = relationship("BorrowOrder", secondary=borrow_order_item, back_populates="books")
    
    def __repr__(self):
        return f"<Book {self.title}>"

class BorrowOrder(Base):
    """
    Model cho đơn mượn sách (có thể mượn nhiều sách trong 1 đơn)
    """
    __tablename__ = "borrow_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=False)
    status = Column(String(20), default="pending")  # pending, approved, active, completed, rejected, overdue
    notes = Column(Text)
    
    # Relationship
    user = relationship("User", back_populates="borrow_orders")
    books = relationship("Book", secondary=borrow_order_item, back_populates="borrow_orders")
    
    def __repr__(self):
        return f"<BorrowOrder {self.id} - User {self.user_id}>"

class Borrow(Base):
    """
    Model cho mượn sách (chi tiết của từng sách trong đơn mượn)
    """
    __tablename__ = "borrows"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("borrow_orders.id"), nullable=True)
    borrow_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=False)
    return_date = Column(DateTime)
    is_returned = Column(Boolean, default=False)
    status = Column(String(20), default="active")  # active, returned, overdue
    notes = Column(Text)
    
    # Relationship
    user = relationship("User", back_populates="borrows")
    book = relationship("Book", back_populates="borrows")
    
    def __repr__(self):
        return f"<Borrow {self.id} - User {self.user_id} - Book {self.book_id}>"

class Notification(Base):
    """
    Model cho thông báo
    """
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(20), default="info")  # info, warning, danger
    is_read = Column(Boolean, default=False)
    is_hidden = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    user = relationship("User", back_populates="notifications")
    
    def __repr__(self):
        return f"<Notification {self.id} - User {self.user_id}>"
