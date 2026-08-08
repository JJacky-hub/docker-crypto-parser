import asyncio
import httpx
import json
import logging
import os
import urllib.request
import urllib.parse
from sqlalchemy.ext.asyncio import AsyncSession
from broker import broker
from database import AsyncSessionLocal
from models import CryptoPrice

import html
import httpx

class TelegramHandler(logging.Handler):
    def __init__(self, token: str, chat_id: str, level=logging.ERROR):
        super().__init__(level)
        self.token = token
        self.chat_id = chat_id
        self.url = f"https://api.telegram.org/bot{self.token}/sendMessage"

    def emit(self, record: logging.LogRecord):
        try:
            log_entry = self.format(record)
            # Экранируем спецсимволы (<, >, &), чтобы Telegram HTML-парсер не выдавал 400 Bad Request
            safe_log_entry = html.escape(log_entry)

            message = f"🚨 <b>[{record.levelname}] Crypto Parser</b>\n<pre>{safe_log_entry}</pre>"

            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }

            with httpx.Client(timeout=10.0) as client:
                client.post(self.url, json=payload)
        except Exception:
            self.handleError(record)

# --- Настройка логгера ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
tg_chat_id = os.getenv("TELEGRAM_CHAT_ID")

if tg_token and tg_chat_id:
    tg_handler = TelegramHandler(token=tg_token, chat_id=tg_chat_id, level=logging.ERROR)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    tg_handler.setFormatter(formatter)
    logger.addHandler(tg_handler)

# --- Настройки парсера ---
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

@broker.task(
    schedule=[
        {
            "cron": "*/10 * * * *",
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
                        logger.info(f"✅ [Worker] {symbol}: ${price}")

                        crypto_price = CryptoPrice(
                            symbol=symbol,
                            price_usd=price,
                            source="MEXC"
                        )
                        db.add(crypto_price)
                    else:
                        # Эта ошибка автоматически уйдет в Telegram
                        logger.error(f"Ошибка API MEXC для {symbol}: status {response.status_code}")
                except Exception as e:
                    # Эта ошибка также отправится в Telegram
                    logger.error(f"Не удалось получить цену для {symbol}: {e}")

            await db.commit()
    logger.info("🎉 [Worker] Сбор котировок завершен!")
