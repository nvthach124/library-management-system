from fastapi import APIRouter, Depends, HTTPException, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime, date

from app.database.db import get_db
from app.database.models import Author
from app.auth.auth import get_current_user, get_user

router = APIRouter(prefix="/api/authors", tags=["authors"])

@router.get("/")
async def get_authors(
    search: Optional[str] = None,
    page: int = Query(1, gt=0),
    limit: int = Query(10, gt=0),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    
    
    query = db.query(Author)
    
    if search:
        query = query.filter(Author.name.ilike(f"%{search}%"))
    
    total = query.count()
    total_pages = (total + limit - 1) // limit
    
    authors = query.offset((page - 1) * limit).limit(limit).all()
    
    return {
        "authors": authors,
        "total": total,
        "page": page,
        "total_pages": total_pages
    }

@router.post("/")
async def create_author(
    name: str = Form(...),
    biography: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    
    
    # Kiểm tra tên tác giả đã tồn tại
    existing = db.query(Author).filter(func.lower(Author.name) == name.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tên tác giả đã tồn tại")
    
    author = Author(
        name=name,
        biography=biography,
        # created_by=current_user["id"]
    )
    
    try:
        db.add(author)
        db.commit()
        db.refresh(author)
        return {"success": True, "author": author}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{id}")
async def update_author(
    id: int,
    name: str = Form(...),
    biography: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if not current_user or not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập")
    
    # Chuẩn hóa dữ liệu input
    name = name.strip()
    if biography:
        biography = biography.strip()
        
    if not name:
        raise HTTPException(status_code=400, detail="Tên tác giả không được để trống")
    
    author = db.query(Author).filter(Author.id == id).first()
    if not author:
        raise HTTPException(status_code=404, detail="Không tìm thấy tác giả")
    
    # Kiểm tra tên tác giả đã tồn tại (trừ chính nó)
    existing = db.query(Author).filter(
        func.lower(Author.name) == name.lower(),
        Author.id != id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tên tác giả đã tồn tại")
    
    try:
        author.name = name
        author.biography = biography
        # author.updated_at = datetime.utcnow()
        # author.updated_by = current_user["id"]
        
        db.commit()
        db.refresh(author)
        return {"success": True, "author": author}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{id}")
async def delete_author(
    id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
  
    
    author = db.query(Author).filter(Author.id == id).first()
    if not author:
        raise HTTPException(status_code=404, detail="Không tìm thấy tác giả")
    
    # Kiểm tra xem tác giả có sách không
    if len(author.books) > 0:
        raise HTTPException(status_code=400, detail="Không thể xóa tác giả đang có sách")
    
    try:
        db.delete(author)
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
