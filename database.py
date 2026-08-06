import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# Получаем данные подключения из переменных окружения
DB_USER = os.getenv("DB_USER", "postgres_user")
DB_PASS = os.getenv("DB_PASS", "super_password")
DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "crypto_db")

# Формируем DSN с асинхронным драйвером postgresql+asyncpg://
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"

# Создаем асинхронный движок SQLAlchemy
engine = create_async_engine(DATABASE_URL, echo=True)

# Фабрика асинхронных сессий для работы с БД
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Базовый класс для всех ORM-моделей
class Base(DeclarativeBase):
    pass

# Зависимость (Dependency) для получения сессии в FastAPI эндпоинтах
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
