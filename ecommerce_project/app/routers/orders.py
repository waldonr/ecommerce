from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import random
import string

from .. import models, schemas
from ..database import get_db
from ..dependencies import get_current_active_user, get_admin_user

router = APIRouter(prefix="/orders", tags=["orders"])

def generate_order_number():
    """Генерация уникального номера заказа"""
    timestamp = datetime.now().strftime("%Y%m%d")
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"ORD-{timestamp}-{random_str}"

def calculate_shipping_cost(shipping_method: str, subtotal: float) -> float:
    """Расчет стоимости доставки"""
    if shipping_method == "express":
        return 15.0
    elif shipping_method == "standard":
        return 5.0 if subtotal < 100 else 0.0  # Бесплатная доставка от 100
    return 0.0

def calculate_tax(subtotal: float) -> float:
    """Расчет налога (упрощенно)"""
    return round(subtotal * 0.1, 2)  # 10% налог

# Создание заказа из корзины
@router.post("/checkout", response_model=schemas.OrderResponse)
def create_order_from_cart(
    checkout_data: schemas.CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Получаем товары из корзины пользователя
    cart_items = db.query(models.CartItem).filter(
        models.CartItem.user_id == current_user.id
    ).all()
    
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    # Проверяем доступность товаров и рассчитываем суммы
    subtotal = 0
    order_items_data = []
    
    for cart_item in cart_items:
        product = db.query(models.Product).filter(
            models.Product.id == cart_item.product_id,
            models.Product.is_active == True
        ).first()
        
        if not product:
            raise HTTPException(
                status_code=404, 
                detail=f"Product {cart_item.product_id} not found"
            )
        
        if product.quantity < cart_item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough stock for {product.name}. Available: {product.quantity}, requested: {cart_item.quantity}"
            )
        
        # Сохраняем информацию о товаре на момент заказа
        item_data = {
            "product_id": product.id,
            "product_name": product.name,
            "product_sku": product.sku,
            "product_price": product.price,
            "quantity": cart_item.quantity
        }
        order_items_data.append(item_data)
        subtotal += product.price * cart_item.quantity
    
    # Рассчитываем итоговые суммы
    shipping_cost = calculate_shipping_cost(checkout_data.shipping_method, subtotal)
    tax_amount = calculate_tax(subtotal)
    total = subtotal + shipping_cost + tax_amount
    
    # Создаем заказ
    order_number = generate_order_number()
    new_order = models.OrderDB(
        order_number=order_number,
        user_id=current_user.id,
        status="pending",
        subtotal=subtotal,
        shipping_cost=shipping_cost,
        tax_amount=tax_amount,
        discount_amount=0,  # Можно добавить систему скидок
        total=total,
        shipping_address=checkout_data.shipping_address,
        shipping_method=checkout_data.shipping_method,
        customer_name=checkout_data.customer_name,
        customer_email=checkout_data.customer_email,
        customer_phone=checkout_data.customer_phone,
        payment_method=checkout_data.payment_method,
        notes=checkout_data.notes
    )
    
    db.add(new_order)
    db.flush()  # Получаем ID заказа без коммита
    
    # Создаем элементы заказа
    for item_data in order_items_data:
        order_item = models.OrderItemDB(
            order_id=new_order.id,
            product_id=item_data["product_id"],
            product_name=item_data["product_name"],
            product_sku=item_data["product_sku"],
            product_price=item_data["product_price"],
            quantity=item_data["quantity"]
        )
        db.add(order_item)
        
        # Обновляем количество товара на складе
        product = db.query(models.Product).filter(models.Product.id == item_data["product_id"]).first()
        product.quantity -= item_data["quantity"]
        product.updated_at = datetime.now().isoformat()
    
    # Очищаем корзину пользователя
    db.query(models.CartItem).filter(models.CartItem.user_id == current_user.id).delete()
    
    db.commit()
    db.refresh(new_order)
    
    # Формируем ответ
    return format_order_response(new_order, db)

# Получить список заказов пользователя
@router.get("/my-orders", response_model=List[schemas.OrderSummary])
def get_my_orders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
    status: Optional[str] = None,
    page: int = 1,
    size: int = 10
):
    query = db.query(models.OrderDB).filter(models.OrderDB.user_id == current_user.id)
    
    if status:
        query = query.filter(models.OrderDB.status == status)
    
    # Пагинация
    offset = (page - 1) * size
    orders = query.order_by(models.OrderDB.created_at.desc()).offset(offset).limit(size).all()
    
    result = []
    for order in orders:
        item_count = db.query(models.OrderItemDB).filter(models.OrderItemDB.order_id == order.id).count()
        result.append(schemas.OrderSummary(
            id=order.id,
            order_number=order.order_number,
            status=order.status,
            total=order.total,
            created_at=order.created_at,
            item_count=item_count
        ))
    
    return result

# Получить детали заказа по ID
@router.get("/{order_id}", response_model=schemas.OrderResponse)
def get_order(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    order = db.query(models.OrderDB).filter(models.OrderDB.id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Проверяем, что пользователь имеет доступ к заказу
    if order.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    return format_order_response(order, db)

# Получить все заказы (для админов)
@router.get("/", response_model=List[schemas.OrderSummary])
def get_all_orders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_admin_user),
    status: Optional[str] = None,
    page: int = 1,
    size: int = 20
):
    query = db.query(models.OrderDB)
    
    if status:
        query = query.filter(models.OrderDB.status == status)
    
    offset = (page - 1) * size
    orders = query.order_by(models.OrderDB.created_at.desc()).offset(offset).limit(size).all()
    
    result = []
    for order in orders:
        item_count = db.query(models.OrderItemDB).filter(models.OrderItemDB.order_id == order.id).count()
        result.append(schemas.OrderSummary(
            id=order.id,
            order_number=order.order_number,
            status=order.status,
            total=order.total,
            created_at=order.created_at,
            item_count=item_count
        ))
    
    return result

# Обновить статус заказа (для админов)
@router.patch("/{order_id}/status", response_model=schemas.OrderResponse)
def update_order_status(
    order_id: str,
    status_update: schemas.OrderUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_admin_user)
):
    order = db.query(models.OrderDB).filter(models.OrderDB.id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if status_update.status:
        valid_statuses = ["pending", "confirmed", "processing", "shipped", "delivered", "cancelled", "refunded"]
        if status_update.status not in valid_statuses:
            raise HTTPException(status_code=400, detail="Invalid status")
        
        order.status = status_update.status
        order.updated_at = datetime.now().isoformat()
        
        # Обновляем даты в зависимости от статуса
        if status_update.status == "shipped" and not order.shipped_at:
            order.shipped_at = datetime.now().isoformat()
        elif status_update.status == "delivered" and not order.delivered_at:
            order.delivered_at = datetime.now().isoformat()
    
    db.commit()
    db.refresh(order)
    
    return format_order_response(order, db)

# Отменить заказ (для пользователя)
@router.post("/{order_id}/cancel", response_model=schemas.OrderResponse)
def cancel_order(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    order = db.query(models.OrderDB).filter(models.OrderDB.id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Проверяем, что пользователь имеет доступ к заказу
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Проверяем, можно ли отменить заказ
    if order.status not in ["pending", "confirmed"]:
        raise HTTPException(
            status_code=400, 
            detail="Cannot cancel order in current status"
        )
    
    # Возвращаем товары на склад
    order_items = db.query(models.OrderItemDB).filter(models.OrderItemDB.order_id == order_id).all()
    for item in order_items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        if product:
            product.quantity += item.quantity
            product.updated_at = datetime.now().isoformat()
    
    order.status = "cancelled"
    order.updated_at = datetime.now().isoformat()
    
    db.commit()
    db.refresh(order)
    
    return format_order_response(order, db)

# Вспомогательная функция для форматирования ответа заказа
def format_order_response(order: models.OrderDB, db: Session) -> schemas.OrderResponse:
    """Форматирует заказ для ответа"""
    order_items = db.query(models.OrderItemDB).filter(models.OrderItemDB.order_id == order.id).all()
    
    items_response = []
    for item in order_items:
        items_response.append(schemas.OrderItemResponse(
            id=item.id,
            product_id=item.product_id,
            product_name=item.product_name,
            product_sku=item.product_sku,
            product_price=item.product_price,
            quantity=item.quantity
        ))
    
    return schemas.OrderResponse(
        id=order.id,
        order_number=order.order_number,
        user_id=order.user_id,
        status=order.status,
        subtotal=order.subtotal,
        shipping_cost=order.shipping_cost,
        tax_amount=order.tax_amount,
        discount_amount=order.discount_amount,
        total=order.total,
        shipping_address=order.shipping_address,
        shipping_method=order.shipping_method,
        customer_name=order.customer_name,
        customer_email=order.customer_email,
        customer_phone=order.customer_phone,
        payment_method=order.payment_method,
        notes=order.notes,
        created_at=order.created_at,
        updated_at=order.updated_at,
        paid_at=order.paid_at,
        shipped_at=order.shipped_at,
        delivered_at=order.delivered_at,
        order_items=items_response
    )