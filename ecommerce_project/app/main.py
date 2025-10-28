from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os
from .database import engine, Base, get_db
from .routers import auth, products, categories, users, cart, orders
from . import models
from .utils.security import get_password_hash

# Создаем таблицы
Base.metadata.create_all(bind=engine)

# Создаем тестового пользователя
def create_test_data():
    db = next(get_db())
    try:
        # Проверяем, есть ли уже пользователи
        user_count = db.query(models.User).count()
        if user_count == 0:
            # Создаем тестового пользователя
            test_user = models.User(
                username="testuser",
                email="test@example.com",
                hashed_password=get_password_hash("secret123"),
                is_admin=True
            )
            db.add(test_user)
            db.commit()
            print("✅ Тестовый пользователь создан: testuser / secret123")
        else:
            print("✅ В базе уже есть пользователи")
    except Exception as e:
        print(f"❌ Ошибка при создании тестовых данных: {e}")
    finally:
        db.close()

# Создаем папки для статических файлов
os.makedirs("static/products", exist_ok=True)
os.makedirs("static/uploads", exist_ok=True)

app = FastAPI(title="Ecommerce API", version="1.0.0")

# Подключаем статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")

# Подключаем роутеры
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(categories.router)
app.include_router(users.router)
app.include_router(cart.router)
app.include_router(orders.router)

@app.on_event("startup")
def on_startup():
    create_test_data()

@app.get("/")
def read_root():
    return {"message": "Ecommerce API is running!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)