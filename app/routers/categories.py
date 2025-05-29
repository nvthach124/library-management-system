from fastapi import APIRouter, Depends, HTTPException, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime

from app.database.db import get_db
from app.database.models import Category
from app.auth.auth import get_current_user, get_user


router = APIRouter(prefix="/api/categories", tags=["categories"])

@router.get("/")
async def get_categories(
    search: Optional[str] = None,
    page: int = Query(1, gt=0),
    limit: int = Query(10, gt=0),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if not current_user or not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Không có quyền truy cập")
    
    query = db.query(Category)
    
    if search:
        query = query.filter(Category.name.ilike(f"%{search}%"))
    
    total = query.count()
    total_pages = (total + limit - 1) // limit
    
    categories = query.offset((page - 1) * limit).limit(limit).all()
    
    return {
        "categories": categories,
        "total": total,
        "page": page,
        "total_pages": total_pages
    }

@router.post("/")
async def create_category(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # if not current_user or not current_user.get("is_admin"):
    #     raise HTTPException(status_code=403, detail="Không có quyền truy cập")
    
    # Kiểm tra trùng tên
    exists = db.query(Category).filter(func.lower(Category.name) == func.lower(name)).first()
    if exists:
        raise HTTPException(status_code=400, detail="Tên danh mục đã tồn tại")
    
    category = Category(
        name=name,
        description=description
    )
    
    try:
        db.add(category)
        db.commit()
        db.refresh(category)
        return category
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Không thể tạo danh mục")

@router.put("/{id}")
async def update_category(
    id: int,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # if not current_user or not current_user.get("is_admin"):
    #     raise HTTPException(status_code=403, detail="Không có quyền truy cập")
    
    category = db.query(Category).filter(Category.id == id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Không tìm thấy danh mục")
    
    # Kiểm tra tên danh mục đã tồn tại (trừ chính nó)
    existing = db.query(Category).filter(
        func.lower(Category.name) == name.lower(),
        Category.id != id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tên danh mục đã tồn tại")
    
    try:
        category.name = name
        category.description = description
        
        db.commit()
        db.refresh(category)
        return {"success": True, "category": category}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{id}")
async def delete_category(
    id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # if not current_user or not current_user.get("is_admin"):
    #     raise HTTPException(status_code=403, detail="Không có quyền truy cập")
    
    category = db.query(Category).filter(Category.id == id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Không tìm thấy danh mục")
    
    # Kiểm tra xem danh mục có sách không
    if len(category.books) > 0:
        raise HTTPException(status_code=400, detail="Không thể xóa danh mục đang có sách")
    
    try:
        db.delete(category)
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
