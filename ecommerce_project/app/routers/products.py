from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from .. import models, schemas
from ..database import get_db
from ..dependencies import get_current_active_user, get_admin_user

router = APIRouter(prefix="/products", tags=["products"])

# Пагинированный ответ для товаров
class PaginatedProductsResponse(BaseModel):
    items: List[schemas.ProductResponse]
    total: int
    page: int
    size: int
    total_pages: int

    class Config:
        from_attributes = True

# Получить все товары с пагинацией и фильтрами
@router.get("/", response_model=PaginatedProductsResponse)
def get_products(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Номер страницы"),
    size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    category_id: Optional[str] = Query(None, description="Фильтр по категории"),
    active_only: bool = Query(True, description="Только активные товары"),
    featured_only: bool = Query(False, description="Только избранные товары"),
    min_price: Optional[float] = Query(None, ge=0, description="Минимальная цена"),
    max_price: Optional[float] = Query(None, ge=0, description="Максимальная цена"),
    search: Optional[str] = Query(None, description="Поиск по названию и описанию"),
    in_stock_only: bool = Query(False, description="Только товары в наличии")
):
    # Базовый запрос
    query = db.query(models.Product)
    
    # Применяем фильтры
    if category_id:
        query = query.filter(models.Product.category_id == category_id)
    
    if active_only:
        query = query.filter(models.Product.is_active == True)
    
    if featured_only:
        query = query.filter(models.Product.is_featured == True)
    
    if min_price is not None:
        query = query.filter(models.Product.price >= min_price)
    
    if max_price is not None:
        query = query.filter(models.Product.price <= max_price)
    
    if in_stock_only:
        query = query.filter(models.Product.quantity > 0)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (models.Product.name.ilike(search_term)) | 
            (models.Product.description.ilike(search_term))
        )
    
    # Вычисляем пагинацию
    total = query.count()
    total_pages = (total + size - 1) // size
    offset = (page - 1) * size
    
    # Получаем товары
    products = query.order_by(models.Product.created_at.desc()).offset(offset).limit(size).all()
    
    return PaginatedProductsResponse(
        items=products,
        total=total,
        page=page,
        size=size,
        total_pages=total_pages
    )

# Получить товар по ID
@router.get("/{product_id}", response_model=schemas.ProductResponse)
def get_product(product_id: str, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

# Создать товар (только для админов)
@router.post("/", response_model=schemas.ProductResponse)
def create_product(
    product: schemas.ProductCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_admin_user)
):
    # Проверяем, существует ли категория
    category = db.query(models.Category).filter(models.Category.id == product.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Проверяем, нет ли товара с таким же SKU
    db_product = db.query(models.Product).filter(models.Product.sku == product.sku).first()
    if db_product:
        raise HTTPException(status_code=400, detail="Product with this SKU already exists")
    
    db_product = models.Product(
        name=product.name,
        description=product.description,
        price=product.price,
        compare_price=product.compare_price,
        quantity=product.quantity,
        sku=product.sku,
        category_id=product.category_id
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

# Обновить товар (только для админов)
@router.put("/{product_id}", response_model=schemas.ProductResponse)
def update_product(
    product_id: str,
    product: schemas.ProductCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_admin_user)
):
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Проверяем, существует ли категория
    category = db.query(models.Category).filter(models.Category.id == product.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Проверяем, не используется ли SKU другим товаром
    existing_product = db.query(models.Product).filter(
        models.Product.sku == product.sku,
        models.Product.id != product_id
    ).first()
    if existing_product:
        raise HTTPException(status_code=400, detail="Product with this SKU already exists")
    
    db_product.name = product.name
    db_product.description = product.description
    db_product.price = product.price
    db_product.compare_price = product.compare_price
    db_product.quantity = product.quantity
    db_product.sku = product.sku
    db_product.category_id = product.category_id
    db.commit()
    db.refresh(db_product)
    return db_product

# Удалить товар (только для админов)
@router.delete("/{product_id}")
def delete_product(
    product_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_admin_user)
):
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db.delete(db_product)
    db.commit()
    return {"message": "Product deleted successfully"}

# Получить товары по категории
@router.get("/category/{category_id}", response_model=List[schemas.ProductResponse])
def get_products_by_category(
    category_id: str,
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100)
):
    # Проверяем существование категории
    category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    products = db.query(models.Product).filter(
        models.Product.category_id == category_id,
        models.Product.is_active == True
    ).limit(limit).all()
    
    return products