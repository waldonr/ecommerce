from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from .. import models, schemas
from ..database import get_db
from ..dependencies import get_current_active_user, get_admin_user

router = APIRouter(prefix="/categories", tags=["categories"])

# Пагинированный ответ для категорий
class PaginatedCategoriesResponse(BaseModel):
    items: List[schemas.CategoryResponse]
    total: int
    page: int
    size: int
    total_pages: int

    class Config:
        from_attributes = True

# Получить все категории с пагинацией
@router.get("/", response_model=PaginatedCategoriesResponse)
def get_categories(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Номер страницы"),
    size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    active_only: bool = Query(True, description="Только активные категории")
):
    # Базовый запрос
    query = db.query(models.Category)
    
    if active_only:
        query = query.filter(models.Category.is_active == True)
    
    # Вычисляем пагинацию
    total = query.count()
    total_pages = (total + size - 1) // size
    offset = (page - 1) * size
    
    # Получаем категории
    categories = query.order_by(models.Category.name).offset(offset).limit(size).all()
    
    return PaginatedCategoriesResponse(
        items=categories,
        total=total,
        page=page,
        size=size,
        total_pages=total_pages
    )

# Получить категорию по ID
@router.get("/{category_id}", response_model=schemas.CategoryResponse)
def get_category(category_id: str, db: Session = Depends(get_db)):
    category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category

# Создать категорию (только для админов)
@router.post("/", response_model=schemas.CategoryResponse)
def create_category(
    category: schemas.CategoryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_admin_user)
):
    # Проверяем, нет ли категории с таким же именем
    db_category = db.query(models.Category).filter(models.Category.name == category.name).first()
    if db_category:
        raise HTTPException(status_code=400, detail="Category with this name already exists")
    
    db_category = models.Category(
        name=category.name,
        description=category.description
    )
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

# Обновить категорию (только для админов)
@router.put("/{category_id}", response_model=schemas.CategoryResponse)
def update_category(
    category_id: str,
    category: schemas.CategoryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_admin_user)
):
    db_category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Проверяем, не используется ли имя другой категорией
    existing_category = db.query(models.Category).filter(
        models.Category.name == category.name,
        models.Category.id != category_id
    ).first()
    if existing_category:
        raise HTTPException(status_code=400, detail="Category with this name already exists")
    
    db_category.name = category.name
    db_category.description = category.description
    db.commit()
    db.refresh(db_category)
    return db_category

# Удалить категорию (только для админов)
@router.delete("/{category_id}")
def delete_category(
    category_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_admin_user)
):
    db_category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Проверяем, есть ли товары в этой категории
    products_count = db.query(models.Product).filter(models.Product.category_id == category_id).count()
    if products_count > 0:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete category with products. Please reassign or delete products first."
        )
    
    db.delete(db_category)
    db.commit()
    return {"message": "Category deleted successfully"}