import os
import asyncio
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, Depends, Query
import httpx
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# 1. Подключение к PostgreSQL
DB_USER = os.getenv("DB_USER", "postgres_user")
DB_PASS = os.getenv("DB_PASS", "super_password")
DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "crypto_db")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. Модель базы данных
class CryptoPrice(Base):
    __tablename__ = "crypto_prices"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    price_usd = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

Base.metadata.create_all(bind=engine)

# 3. FastAPI Инициализация
app = FastAPI(title="Crypto Analytics Platform", version="2.0")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 4. Фоновый асинхронный воркер (CoinGecko API)
async def fetch_crypto_prices():
    """Фоновая задача: запрашивает цены с CoinGecko каждые 15 секунд"""
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd"
    
    # Маппинг ID CoinGecko -> Наше имя тикера
    mapping = {
        "bitcoin": "BTCUSDT",
        "ethereum": "ETHUSDT",
        "solana": "SOLUSDT"
    }

    print("[WORKER] Фоновый сборщик цен запущен!", flush=True)

    while True:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    db = SessionLocal()
                    saved_dict = {}
                    
                    for coin_id, symbol in mapping.items():
                        if coin_id in data:
                            price = float(data[coin_id]["usd"])
                            record = CryptoPrice(symbol=symbol, price_usd=price, timestamp=datetime.utcnow())
                            db.add(record)
                            saved_dict[symbol] = price
                            
                    db.commit()
                    db.close()
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Успешно сохранены цены: {saved_dict}", flush=True)
                else:
                    print(f"[WORKER ERROR] Ошибка API: статус {response.status_code}", flush=True)
        except Exception as e:
            print(f"[WORKER ERROR] Сбой запроса: {e}", flush=True)
            
        await asyncio.sleep(15)  # Запрос каждые 15 секунд

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(fetch_crypto_prices())

# 5. REST API Эндпоинты
@app.get("/")
def root():
    return {"status": "Parser is running", "version": "2.0"}

@app.get("/api/prices/latest")
def get_latest_prices(db: Session = Depends(get_db)):
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    result = {}
    for symbol in symbols:
        latest = db.query(CryptoPrice).filter(CryptoPrice.symbol == symbol).order_by(CryptoPrice.timestamp.desc()).first()
        if latest:
            result[symbol] = {
                "price_usd": latest.price_usd,
                "timestamp": latest.timestamp.isoformat()
            }
    return result

@app.get("/api/prices/history/{symbol}")
def get_price_history(symbol: str, limit: int = Query(20, le=100), db: Session = Depends(get_db)):
    history = db.query(CryptoPrice).filter(CryptoPrice.symbol == symbol.upper()).order_by(CryptoPrice.timestamp.desc()).limit(limit).all()
    return [
        {"price_usd": record.price_usd, "timestamp": record.timestamp.isoformat()}
        for record in history
    ]
