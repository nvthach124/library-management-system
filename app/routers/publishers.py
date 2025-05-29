from fastapi import APIRouter, Depends, HTTPException, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime

from app.database.db import get_db
from app.database.models import Publisher
from app.auth.auth import get_current_user, get_user

router = APIRouter(prefix="/api/publishers", tags=["publishers"])

@router.get("/")
async def get_publishers(
    search: Optional[str] = None,
    page: int = Query(1, gt=0),
    limit: int = Query(10, gt=0),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if not current_user or not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập")
    
    query = db.query(Publisher)
    
    if search:
        search = search.strip()
        query = query.filter(Publisher.name.ilike(f"%{search}%"))
    
    total = query.count()
    total_pages = (total + limit - 1) // limit
    
    publishers = query.offset((page - 1) * limit).limit(limit).all()
    
    return {
        "publishers": publishers,
        "total": total,
        "page": page,
        "total_pages": total_pages
    }

@router.post("/")
async def create_publisher(
    name: str = Form(...),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if not current_user or not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập")
    
    # Chuẩn hóa dữ liệu input
    name = name.strip()
    if email:
        email = email.strip()
    if phone:
        phone = phone.strip()
    if address:
        address = address.strip()
        
    if not name:
        raise HTTPException(status_code=400, detail="Tên nhà xuất bản không được để trống")
    
    # Kiểm tra tên nhà xuất bản đã tồn tại
    existing = db.query(Publisher).filter(func.lower(Publisher.name) == name.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tên nhà xuất bản đã tồn tại")
    
    publisher = Publisher(
        name=name,
        email=email,
        phone=phone,
        address=address
    )
    
    try:
        db.add(publisher)
        db.commit()
        db.refresh(publisher)
        return {"success": True, "publisher": publisher}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{id}")
async def update_publisher(
    id: int,
    name: str = Form(...),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if not current_user or not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập")
    
    # Chuẩn hóa dữ liệu input
    name = name.strip()
    if email:
        email = email.strip()
    if phone:
        phone = phone.strip()
    if address:
        address = address.strip()
        
    if not name:
        raise HTTPException(status_code=400, detail="Tên nhà xuất bản không được để trống")
    
    publisher = db.query(Publisher).filter(Publisher.id == id).first()
    if not publisher:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhà xuất bản")
    
    # Kiểm tra tên nhà xuất bản đã tồn tại (trừ chính nó)
    existing = db.query(Publisher).filter(
        func.lower(Publisher.name) == name.lower(),
        Publisher.id != id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tên nhà xuất bản đã tồn tại")
    
    try:
        publisher.name = name
        publisher.email = email
        publisher.phone = phone
        publisher.address = address
        
        db.commit()
        db.refresh(publisher)
        return {"success": True, "publisher": publisher}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{id}")
async def delete_publisher(
    id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if not current_user or not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập")
    
    publisher = db.query(Publisher).filter(Publisher.id == id).first()
    if not publisher:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhà xuất bản")
    
    # Kiểm tra xem nhà xuất bản có sách không
    if len(publisher.books) > 0:
        raise HTTPException(status_code=400, detail="Không thể xóa nhà xuất bản đang có sách")
    
    try:
        db.delete(publisher)
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
