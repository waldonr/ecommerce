from sqlalchemy import Column, String, Boolean, Integer, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from .database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(String, default=lambda: datetime.now().isoformat())

    cart_items = relationship("CartItem", back_populates="user")
    orders = relationship("OrderDB", back_populates="user")

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(String, default=lambda: datetime.now().isoformat())
    
    products = relationship("Product", back_populates="category")
    #order_items = relationship("OrderItemDB", back_populates="product")

class Product(Base):
    __tablename__ = "products"
    
    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    name = Column(String, index=True)
    description = Column(Text)
    price = Column(Float, nullable=False)
    compare_price = Column(Float, nullable=True)
    quantity = Column(Integer, default=0)
    sku = Column(String, unique=True, index=True)
    
    category_id = Column(String, ForeignKey("categories.id"))
    category = relationship("Category", back_populates="products")
    
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    created_at = Column(String, default=lambda: datetime.now().isoformat())
    updated_at = Column(String, default=lambda: datetime.now().isoformat())

    cart_items = relationship("CartItem", back_populates="product")
    order_items = relationship("OrderItemDB", back_populates="product")

class CartItem(Base):
    __tablename__ = "cart_items"
    
    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    added_at = Column(String, default=lambda: datetime.now().isoformat())
    updated_at = Column(String, default=lambda: datetime.now().isoformat())
    
    # Связи
    user = relationship("User", back_populates="cart_items")
    product = relationship("Product", back_populates="cart_items")

class OrderDB(Base):
    __tablename__ = "orders"
    
    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    order_number = Column(String, unique=True, index=True)  # Человеко-читаемый номер
    
    # Пользователь
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Статус заказа
    status = Column(String, default="pending")  # pending, confirmed, processing, shipped, delivered, cancelled, refunded
    
    # Суммы
    subtotal = Column(Float, default=0)  # Сумма товаров
    shipping_cost = Column(Float, default=0)  # Стоимость доставки
    tax_amount = Column(Float, default=0)  # Налоги
    discount_amount = Column(Float, default=0)  # Скидка
    total = Column(Float, default=0)  # Итоговая сумма
    
    # Информация о доставке
    shipping_address = Column(Text)  # Упростим - храним как текст
    shipping_method = Column(String, default="standard")  # standard, express
    
    # Контактная информация
    customer_name = Column(String)
    customer_email = Column(String)
    customer_phone = Column(String, nullable=True)
    
    # Даты
    created_at = Column(String, default=lambda: datetime.now().isoformat())
    updated_at = Column(String, default=lambda: datetime.now().isoformat())
    paid_at = Column(String, nullable=True)
    shipped_at = Column(String, nullable=True)
    delivered_at = Column(String, nullable=True)
    
    # Дополнительная информация
    notes = Column(Text, nullable=True)
    payment_method = Column(String, default="card")  # card, cash, etc.
    
    # Связи
    user = relationship("User", back_populates="orders")
    order_items = relationship("OrderItemDB", back_populates="order", cascade="all, delete-orphan")

class OrderItemDB(Base):
    __tablename__ = "order_items"
    
    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    
    # Информация о товаре на момент заказа (на случай изменения товара)
    product_name = Column(String)
    product_sku = Column(String)
    product_price = Column(Float)  # Цена на момент заказа
    quantity = Column(Integer)
    
    # Связи
    order = relationship("OrderDB", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")