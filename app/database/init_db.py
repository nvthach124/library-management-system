import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database.db import engine, Base
from app.database.models import User, Category, Author, Publisher, Book, Borrow, book_category
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import random
from datetime import datetime, timedelta

# Tạo một context để băm mật khẩu
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hàm băm mật khẩu
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def init_db():
    """
    Hàm khởi tạo database và tạo dữ liệu mẫu
    """
    print("Đang tạo cấu trúc database...")
    Base.metadata.create_all(bind=engine)
    print("Đã tạo cấu trúc database thành công!")
    
    # Kiểm tra xem đã có dữ liệu mẫu chưa
    db = Session(engine)
    user_count = db.query(User).count()
    
    if user_count == 0:
        print("Đang tạo dữ liệu mẫu...")
        create_sample_data(db)
        print("Đã tạo dữ liệu mẫu thành công!")
    else:
        print("Dữ liệu mẫu đã tồn tại!")
    
    db.close()

def create_sample_data(db: Session):
    """
    Tạo dữ liệu mẫu cho database
    """
    # Tạo tài khoản admin
    admin_password = get_password_hash("admin123")
    admin = User(
        full_name="Quản Trị Viên",
        email="admin@thuvien.com",
        phone_number="0987654321",
        address="123 Đường ABC, Quận XYZ, TP HN",
        username="admin",
        password=admin_password,
        is_admin=True
    )
    db.add(admin)
    
    # Tạo tài khoản user
    user_password = get_password_hash("user123")
    user = User(
        full_name="Người Dùng",
        email="user@example.com",
        phone_number="0123456789",
        address="456 Đường XYZ, Quận ABC, TP HN",
        username="user",
        password=user_password,
        is_admin=False
    )
    db.add(user)
    
    # Tạo các thể loại sách
    categories = [
        Category(name="Tâm Lý - Kỹ Năng Sống", icon="fa-brain", 
                description="Sách về tâm lý học và kỹ năng sống giúp phát triển bản thân"),
        Category(name="Văn Học Việt Nam", icon="fa-landmark", 
                description="Các tác phẩm văn học Việt Nam từ cổ điển đến hiện đại"),
        Category(name="Văn Học Nước Ngoài", icon="fa-globe", 
                description="Các tác phẩm văn học nổi tiếng của các tác giả nước ngoài"),
        Category(name="Kinh Tế - Quản Trị", icon="fa-chart-line", 
                description="Sách về kinh doanh, quản trị và tài chính"),
        Category(name="Giáo Trình", icon="fa-book", 
                description="Sách giáo khoa và giáo trình đại học"),
        Category(name="Khoa Học - Công Nghệ", icon="fa-flask", 
                description="Sách về khoa học, công nghệ và tin học")
    ]
    
    for category in categories:
        db.add(category)
    
    # Tạo các tác giả
    authors = [
        Author(name="Nguyễn Du", biography="Đại thi hào dân tộc, tác giả Truyện Kiều"),
        Author(name="Dale Carnegie", biography="Tác giả người Mỹ nổi tiếng với những cuốn sách về kỹ năng sống"),
        Author(name="Paulo Coelho", biography="Nhà văn người Brazil nổi tiếng với tác phẩm Nhà Giả Kim"),
        Author(name="David J. Lieberman", biography="Chuyên gia tâm lý học hàng đầu thế giới"),
        Author(name="Daniel Kahneman", biography="Nhà tâm lý học được trao giải Nobel Kinh tế"),
        Author(name="Nguyễn Nhật Ánh", biography="Nhà văn Việt Nam nổi tiếng với nhiều tác phẩm dành cho giới trẻ"),
        Author(name="J.K. Rowling", biography="Nữ nhà văn người Anh, tác giả bộ truyện Harry Potter")
    ]
    
    for author in authors:
        db.add(author)
    
    # Tạo nhà xuất bản
    publishers = [
        Publisher(name="NXB Văn Học", address="Hà Nội", phone="0123456789", email="vanhoc@nxb.vn"),
        Publisher(name="NXB Trẻ", address="TP HCM", phone="0987654321", email="tre@nxb.vn"),
        Publisher(name="NXB Kim Đồng", address="Hà Nội", phone="0369852147", email="kimdong@nxb.vn"),
        Publisher(name="NXB Tổng Hợp", address="TP HCM", phone="0258741369", email="tonghop@nxb.vn"),
        Publisher(name="NXB Giáo Dục", address="Hà Nội", phone="0147852369", email="giaoduc@nxb.vn")
    ]
    
    for publisher in publishers:
        db.add(publisher)
    
    # Commit các thay đổi để có ID cho mỗi record
    db.commit()
    
    # Lấy dữ liệu đã tạo
    all_categories = db.query(Category).all()
    all_authors = db.query(Author).all()
    all_publishers = db.query(Publisher).all()
    
    # Tạo sách
    books = [
        Book(
            title="Truyện Kiều",
            isbn="9786049652356",
            publication_year=1820,
            pages=248,
            language="Tiếng Việt",
            description="Truyện Kiều hay còn gọi là Đoạn Trường Tân Thanh là một tác phẩm văn học kinh điển của Việt Nam.",
            cover_image="/static/images/book_covers/truyen_kieu.jpg",
            total_copies=20,
            available_copies=15,
            author_id=all_authors[0].id,  # Nguyễn Du
            publisher_id=all_publishers[0].id  # NXB Văn Học
        ),
        Book(
            title="Đắc Nhân Tâm",
            isbn="9786049457678",
            publication_year=1936,
            pages=320,
            language="Tiếng Việt",
            description="Đắc Nhân Tâm là tác phẩm nổi tiếng và bán chạy nhất của Dale Carnegie.",
            cover_image="/static/images/book_covers/dac_nhan_tam.jpg",
            total_copies=15,
            available_copies=12,
            author_id=all_authors[1].id,  # Dale Carnegie
            publisher_id=all_publishers[3].id  # NXB Tổng Hợp
        ),
        Book(
            title="Nhà Giả Kim",
            isbn="9786045891712",
            publication_year=1988,
            pages=228,
            language="Tiếng Việt",
            description="Tác phẩm kể về hành trình phiêu lưu của Santiago, một chàng chăn cừu người Tây Ban Nha.",
            cover_image="/static/images/book_covers/nha_gia_kim.jpg",
            total_copies=18,
            available_copies=16,
            author_id=all_authors[2].id,  # Paulo Coelho
            publisher_id=all_publishers[1].id  # NXB Trẻ
        ),
        Book(
            title="Đọc Vị Bất Kỳ Ai",
            isbn="9786042037129",
            publication_year=2010,
            pages=264,
            language="Tiếng Việt",
            description="Cuốn sách giúp bạn đọc vị đối phương thông qua ngôn ngữ cơ thể và các dấu hiệu tâm lý.",
            cover_image="/static/images/book_covers/doc_vi_bat_ky_ai.jpg",
            total_copies=12,
            available_copies=10,
            author_id=all_authors[3].id,  # David J. Lieberman
            publisher_id=all_publishers[1].id  # NXB Trẻ
        ),
        Book(
            title="Tư Duy Nhanh Và Chậm",
            isbn="9786042213622",
            publication_year=2011,
            pages=612,
            language="Tiếng Việt",
            description="Cuốn sách mô tả hai hệ thống tư duy ảnh hưởng đến cách con người đưa ra quyết định.",
            cover_image="/static/images/book_covers/tu_duy_nhanh_cham.jpg",
            total_copies=10,
            available_copies=9,
            author_id=all_authors[4].id,  # Daniel Kahneman
            publisher_id=all_publishers[3].id  # NXB Tổng Hợp
        ),
        Book(
            title="Cho Tôi Xin Một Vé Đi Tuổi Thơ",
            isbn="9786042028769",
            publication_year=2008,
            pages=208,
            language="Tiếng Việt",
            description="Tác phẩm xoay quanh những kỷ niệm tuổi thơ trong trẻo, hồn nhiên của nhân vật chính.",
            cover_image="/static/images/book_covers/cho_toi_xin_mot_ve.jpg",
            total_copies=20,
            available_copies=18,
            author_id=all_authors[5].id,  # Nguyễn Nhật Ánh
            publisher_id=all_publishers[1].id  # NXB Trẻ
        ),
        Book(
            title="Harry Potter và Hòn Đá Phù Thủy",
            isbn="9786042183932",
            publication_year=1997,
            pages=366,
            language="Tiếng Việt",
            description="Cuốn sách đầu tiên trong bộ truyện Harry Potter nổi tiếng thế giới.",
            cover_image="/static/images/book_covers/harry_potter.jpg",
            total_copies=25,
            available_copies=20,
            author_id=all_authors[6].id,  # J.K. Rowling
            publisher_id=all_publishers[2].id  # NXB Kim Đồng
        )
    ]
    
    for book in books:
        db.add(book)
    
    # Commit để lấy ID cho book
    db.commit()
    
    # Lấy tất cả sách
    all_books = db.query(Book).all()
    
    # Thêm thể loại cho sách
    # Truyện Kiều - Văn Học Việt Nam
    all_books[0].categories.append(all_categories[1])  # Văn Học Việt Nam
    
    # Đắc Nhân Tâm - Tâm Lý - Kỹ Năng Sống, Kinh Tế - Quản Trị
    all_books[1].categories.append(all_categories[0])  # Tâm Lý - Kỹ Năng Sống
    all_books[1].categories.append(all_categories[3])  # Kinh Tế - Quản Trị
    
    # Nhà Giả Kim - Văn Học Nước Ngoài, Tâm Lý - Kỹ Năng Sống
    all_books[2].categories.append(all_categories[2])  # Văn Học Nước Ngoài
    all_books[2].categories.append(all_categories[0])  # Tâm Lý - Kỹ Năng Sống
    
    # Đọc Vị Bất Kỳ Ai - Tâm Lý - Kỹ Năng Sống
    all_books[3].categories.append(all_categories[0])  # Tâm Lý - Kỹ Năng Sống
    
    # Tư Duy Nhanh Và Chậm - Tâm Lý - Kỹ Năng Sống, Khoa Học - Công Nghệ
    all_books[4].categories.append(all_categories[0])  # Tâm Lý - Kỹ Năng Sống
    all_books[4].categories.append(all_categories[5])  # Khoa Học - Công Nghệ
    
    # Cho Tôi Xin Một Vé Đi Tuổi Thơ - Văn Học Việt Nam
    all_books[5].categories.append(all_categories[1])  # Văn Học Việt Nam
    
    # Harry Potter - Văn Học Nước Ngoài
    all_books[6].categories.append(all_categories[2])  # Văn Học Nước Ngoài
    
    # Tạo một số bản ghi mượn sách
    now = datetime.utcnow()
    
    # User mượn "Đọc Vị Bất Kỳ Ai" - chưa trả
    borrow1 = Borrow(
        user_id=user.id,
        book_id=all_books[3].id,  # Đọc Vị Bất Kỳ Ai
        borrow_date=now - timedelta(days=10),
        due_date=now + timedelta(days=10),
        is_returned=False,
        status="active",
        notes="Sách còn mới, cần giữ gìn cẩn thận"
    )
    db.add(borrow1)
    
    # User mượn "Nhà Giả Kim" - đã trả
    borrow2 = Borrow(
        user_id=user.id,
        book_id=all_books[2].id,  # Nhà Giả Kim
        borrow_date=now - timedelta(days=30),
        due_date=now - timedelta(days=15),
        return_date=now - timedelta(days=20),
        is_returned=True,
        status="returned",
        notes="Sách đã được trả đúng hạn"
    )
    db.add(borrow2)
    
    # Commit tất cả thay đổi
    db.commit()

if __name__ == "__main__":
    init_db()
 