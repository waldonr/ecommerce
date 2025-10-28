from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from .. import models, schemas
from ..database import get_db
from ..dependencies import get_current_active_user

router = APIRouter(prefix="/cart", tags=["cart"])

# Получить корзину пользователя
@router.get("/", response_model=schemas.CartResponse)
def get_cart(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Получаем все товары в корзине пользователя
    cart_items = db.query(models.CartItem).filter(
        models.CartItem.user_id == current_user.id
    ).all()
    
    # Собираем информацию о товарах
    items_with_products = []
    total_price = 0
    total_items = 0
    
    for cart_item in cart_items:
        # Получаем информацию о товаре
        product = db.query(models.Product).filter(
            models.Product.id == cart_item.product_id
        ).first()
        
        if product and product.is_active:
            product_info = schemas.ProductInCart(
                id=product.id,
                name=product.name,
                price=product.price,
                sku=product.sku,
                is_active=product.is_active,
                available_quantity=product.quantity
            )
            
            item_response = schemas.CartItemResponse(
                id=cart_item.id,
                product_id=cart_item.product_id,
                quantity=cart_item.quantity,
                added_at=cart_item.added_at,
                updated_at=cart_item.updated_at,
                product=product_info
            )
            
            items_with_products.append(item_response)
            total_price += product.price * cart_item.quantity
            total_items += cart_item.quantity
    
    return schemas.CartResponse(
        items=items_with_products,
        total_items=total_items,
        total_price=round(total_price, 2),
        total_unique_items=len(items_with_products)
    )

# Добавить товар в корзину
@router.post("/", response_model=schemas.CartItemResponse)
def add_to_cart(
    cart_item: schemas.CartItemCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Проверяем существование товара
    product = db.query(models.Product).filter(
        models.Product.id == cart_item.product_id,
        models.Product.is_active == True
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Проверяем доступное количество
    if cart_item.quantity > product.quantity:
        raise HTTPException(
            status_code=400, 
            detail=f"Not enough stock. Available: {product.quantity}"
        )
    
    # Проверяем, есть ли уже этот товар в корзине
    existing_cart_item = db.query(models.CartItem).filter(
        models.CartItem.user_id == current_user.id,
        models.CartItem.product_id == cart_item.product_id
    ).first()
    
    if existing_cart_item:
        # Обновляем количество, если товар уже в корзине
        new_quantity = existing_cart_item.quantity + cart_item.quantity
        
        # Проверяем, не превышает ли новое количество доступное
        if new_quantity > product.quantity:
            raise HTTPException(
                status_code=400, 
                detail=f"Not enough stock. Available: {product.quantity}, already in cart: {existing_cart_item.quantity}"
            )
        
        existing_cart_item.quantity = new_quantity
        existing_cart_item.updated_at = datetime.now().isoformat()
        db.commit()
        db.refresh(existing_cart_item)
        
        # Создаем ответ
        product_info = schemas.ProductInCart(
            id=product.id,
            name=product.name,
            price=product.price,
            sku=product.sku,
            is_active=product.is_active,
            available_quantity=product.quantity
        )
        
        return schemas.CartItemResponse(
            id=existing_cart_item.id,
            product_id=existing_cart_item.product_id,
            quantity=existing_cart_item.quantity,
            added_at=existing_cart_item.added_at,
            updated_at=existing_cart_item.updated_at,
            product=product_info
        )
    else:
        # Создаем новую запись в корзине
        new_cart_item = models.CartItem(
            user_id=current_user.id,
            product_id=cart_item.product_id,
            quantity=cart_item.quantity
        )
        
        db.add(new_cart_item)
        db.commit()
        db.refresh(new_cart_item)
        
        # Создаем ответ
        product_info = schemas.ProductInCart(
            id=product.id,
            name=product.name,
            price=product.price,
            sku=product.sku,
            is_active=product.is_active,
            available_quantity=product.quantity
        )
        
        return schemas.CartItemResponse(
            id=new_cart_item.id,
            product_id=new_cart_item.product_id,
            quantity=new_cart_item.quantity,
            added_at=new_cart_item.added_at,
            updated_at=new_cart_item.updated_at,
            product=product_info
        )

# Обновить количество товара в корзине
@router.put("/{item_id}", response_model=schemas.CartItemResponse)
def update_cart_item(
    item_id: str,
    cart_update: schemas.CartItemUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Находим товар в корзине
    cart_item = db.query(models.CartItem).filter(
        models.CartItem.id == item_id,
        models.CartItem.user_id == current_user.id
    ).first()
    
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    
    # Проверяем товар
    product = db.query(models.Product).filter(
        models.Product.id == cart_item.product_id,
        models.Product.is_active == True
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Проверяем доступное количество
    if cart_update.quantity > product.quantity:
        raise HTTPException(
            status_code=400, 
            detail=f"Not enough stock. Available: {product.quantity}"
        )
    
    if cart_update.quantity <= 0:
        # Если количество <= 0, удаляем товар из корзины
        db.delete(cart_item)
        db.commit()
        raise HTTPException(status_code=200, detail="Item removed from cart")
    
    # Обновляем количество
    cart_item.quantity = cart_update.quantity
    cart_item.updated_at = datetime.now().isoformat()
    db.commit()
    db.refresh(cart_item)
    
    # Создаем ответ
    product_info = schemas.ProductInCart(
        id=product.id,
        name=product.name,
        price=product.price,
        sku=product.sku,
        is_active=product.is_active,
        available_quantity=product.quantity
    )
    
    return schemas.CartItemResponse(
        id=cart_item.id,
        product_id=cart_item.product_id,
        quantity=cart_item.quantity,
        added_at=cart_item.added_at,
        updated_at=cart_item.updated_at,
        product=product_info
    )

# Удалить товар из корзины
@router.delete("/{item_id}")
def remove_from_cart(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    cart_item = db.query(models.CartItem).filter(
        models.CartItem.id == item_id,
        models.CartItem.user_id == current_user.id
    ).first()
    
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    
    db.delete(cart_item)
    db.commit()
    
    return {"message": "Item removed from cart"}

# Очистить корзину
@router.delete("/")
def clear_cart(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    cart_items = db.query(models.CartItem).filter(
        models.CartItem.user_id == current_user.id
    ).all()
    
    for item in cart_items:
        db.delete(item)
    
    db.commit()
    
    return {"message": "Cart cleared successfully"}