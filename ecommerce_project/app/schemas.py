from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: str
    is_active: bool
    is_admin: bool
    created_at: str

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: str
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True

class ProductBase(BaseModel):
    name: str
    description: str
    price: float
    compare_price: Optional[float] = None
    quantity: int = 0
    sku: str

class ProductCreate(ProductBase):
    category_id: str

class ProductResponse(ProductBase):
    id: str
    category_id: str
    is_active: bool
    is_featured: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

class CartItemBase(BaseModel):
    product_id: str
    quantity: int

class CartItemCreate(CartItemBase):
    pass

class CartItemUpdate(BaseModel):
    quantity: int

# Схема для товара в корзине (включает информацию о продукте)
class ProductInCart(BaseModel):
    id: str
    name: str
    price: float
    sku: str
    is_active: bool
    available_quantity: int  # Количество на складе

    class Config:
        from_attributes = True

class CartItemResponse(BaseModel):
    id: str
    product_id: str
    quantity: int
    added_at: str
    updated_at: str
    product: ProductInCart  # Вложенная информация о товаре

    class Config:
        from_attributes = True

class CartResponse(BaseModel):
    items: List[CartItemResponse]
    total_items: int
    total_price: float
    total_unique_items: int

    class Config:
        from_attributes = True

class OrderItemBase(BaseModel):
    product_id: str
    quantity: int

class OrderItemCreate(OrderItemBase):
    pass

class OrderItemResponse(BaseModel):
    id: str
    product_id: str
    product_name: str
    product_sku: str
    product_price: float
    quantity: int

    class Config:
        from_attributes = True

class OrderBase(BaseModel):
    shipping_address: str
    customer_name: str
    customer_email: EmailStr
    customer_phone: Optional[str] = None
    shipping_method: str = "standard"
    payment_method: str = "card"
    notes: Optional[str] = None

class OrderCreate(OrderBase):
    pass

class OrderUpdate(BaseModel):
    status: Optional[str] = None
    shipping_address: Optional[str] = None
    notes: Optional[str] = None

class OrderResponse(BaseModel):
    id: str
    order_number: str
    user_id: str
    status: str
    subtotal: float
    shipping_cost: float
    tax_amount: float
    discount_amount: float
    total: float
    shipping_address: str
    shipping_method: str
    customer_name: str
    customer_email: str
    customer_phone: Optional[str]
    payment_method: str
    notes: Optional[str]
    created_at: str
    updated_at: str
    paid_at: Optional[str]
    shipped_at: Optional[str]
    delivered_at: Optional[str]
    order_items: List[OrderItemResponse]

    class Config:
        from_attributes = True

class OrderSummary(BaseModel):
    id: str
    order_number: str
    status: str
    total: float
    created_at: str
    item_count: int

    class Config:
        from_attributes = True

class CheckoutRequest(BaseModel):
    shipping_address: str
    customer_name: str
    customer_email: EmailStr
    customer_phone: Optional[str] = None
    shipping_method: str = "standard"
    payment_method: str = "card"
    notes: Optional[str] = None