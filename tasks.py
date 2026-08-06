import asyncio
import httpx
import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from broker import broker
from database import AsyncSessionLocal
from models import CryptoPrice

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Список отслеживаемых торговых пар
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "TONUSDT"]

@broker.task
    schedule=[
        {
            "cron": "*/10 * * * * *",  # Запуск каждые 10 секунд
        }
    ]
)
async def fetch_and_store_prices():
    """Фоновая задача Taskiq: забирает цены с MEXC и сохраняет в БД."""
    logger.info("🚀 [Worker] Начинаем сбор котировок...")
    
    async with httpx.AsyncClient() as client:
        async with AsyncSessionLocal() as db:
            for symbol in SYMBOLS:
                try:
                    response = await client.get(
                        f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}",
                        timeout=5.0
                    )
                    if response.status_code == 200:
                        data = response.json()
                        price = float(data["price"])
                        
                        # Сохраняем в PostgreSQL
                        crypto_entry = CryptoPrice(
                            symbol=symbol,
                            price_usd=price,
                            source="MEXC"
                        )
                        db.add(crypto_entry)
                        
                        logger.info(f"✅ [Worker] {symbol}: ${price}")
                    else:
                        logger.warning(f"⚠️ Ошибка API MEXC для {symbol}: status {response.status_code}")
                except Exception as e:
                    logger.error(f"❌ Ошибка при запросе {symbol}: {e}")
            
            await db.commit()
    logger.info("🎉 [Worker] Сбор котировок завершен!")
