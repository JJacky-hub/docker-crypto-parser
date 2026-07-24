import os
import asyncio
import json
from datetime import datetime
from typing import List

from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import httpx
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
import redis.asyncio as aioredis

# 1. Настройки БД и Redis
DB_USER = os.getenv("DB_USER", "postgres_user")
DB_PASS = os.getenv("DB_PASS", "super_password")
DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "crypto_db")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"
REDIS_URL = f"redis://{REDIS_HOST}:6379"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Клиент Redis
redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)

class CryptoPrice(Base):
    __tablename__ = "crypto_prices"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    price_usd = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Crypto Analytics & HighLoad Platform", version="4.0")

# 2. Менеджер WebSockets
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

# 3. Слушатель Redis Pub/Sub (рассылает из шины Redis в WebSockets)
async def redis_pubsub_listener():
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("crypto_prices_channel")
    
    async for message in pubsub.listen():
        if message["type"] == "message":
            data = json.loads(message["data"])
            await manager.broadcast(data)

# 4. Фоновый воркер (Парсит -> Сохраняет в Postgres -> Кэширует в Redis -> Публикует в Pub/Sub)
async def fetch_crypto_prices():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd"
    mapping = {"bitcoin": "BTCUSDT", "ethereum": "ETHUSDT", "solana": "SOLUSDT"}

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
                    
                    current_time = datetime.now().strftime('%H:%M:%S')
                    payload = {"time": current_time, "prices": saved_dict}

                    # А) Кэшируем самые свежие цены в Redis (для моментального REST API)
                    await redis_client.set("latest_crypto_prices", json.dumps(payload))
                    
                    # Б) Публикуем в шину сообщений Redis Pub/Sub
                    await redis_client.publish("crypto_prices_channel", json.dumps(payload))
                    
                    print(f"[{current_time}] [REDIS + DB SUCCESS] {saved_dict}", flush=True)
        except Exception as e:
            print(f"[WORKER ERROR] {e}", flush=True)
            
        await asyncio.sleep(15)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(fetch_crypto_prices())
    asyncio.create_task(redis_pubsub_listener())

# 5. Мгновенный REST API эндпоинт из кэша Redis (без обращения к PostgreSQL!)
@app.get("/api/prices/latest-fast")
async def get_latest_prices_fast():
    cached_data = await redis_client.get("latest_crypto_prices")
    if cached_data:
        return {"source": "redis_cache", "data": json.loads(cached_data)}
    return {"source": "cache_miss", "message": "Данные еще не закэшированы"}

# 6. WebSocket эндпоинт
@app.websocket("/ws/prices")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# 7. Дашборд
@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard():
    return """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Crypto Redis HighLoad Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body { font-family: Arial, sans-serif; background: #121212; color: #fff; text-align: center; margin: 20px; }
            .container { width: 80%; margin: 0 auto; background: #1e1e1e; padding: 20px; border-radius: 12px; }
            .status { font-weight: bold; margin-bottom: 20px; color: #4caf50; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>⚡ Crypto Real-time Dashboard (Powered by Redis Pub/Sub)</h2>
            <div id="status" class="status">Подключение к WebSocket...</div>
            <canvas id="cryptoChart"></canvas>
        </div>

        <script>
            const ctx = document.getElementById('cryptoChart').getContext('2d');
            const cryptoChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        { label: 'BTC ($)', borderColor: '#f2a900', data: [], fill: false },
                        { label: 'ETH ($)', borderColor: '#3c3c3d', data: [], fill: false },
                        { label: 'SOL ($)', borderColor: '#14f195', data: [], fill: false }
                    ]
                },
                options: {
                    responsive: true,
                    scales: {
                        x: { display: true, title: { display: true, text: 'Время' } },
                        y: { display: true, title: { display: true, text: 'Цена USD' } }
                    }
                }
            });

            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/prices`);

            ws.onopen = () => {
                document.getElementById('status').innerText = '🟢 WebSocket + Redis Pub/Sub Активен';
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                const time = data.time;
                const prices = data.prices;

                cryptoChart.data.labels.push(time);
                cryptoChart.data.datasets[0].data.push(prices.BTCUSDT);
                cryptoChart.data.datasets[1].data.push(prices.ETHUSDT);
                cryptoChart.data.datasets[2].data.push(prices.SOLUSDT);

                if (cryptoChart.data.labels.length > 20) {
                    cryptoChart.data.labels.shift();
                    cryptoChart.data.datasets.forEach(d => d.data.shift());
                }

                cryptoChart.update();
            };

            ws.onclose = () => {
                document.getElementById('status').innerText = '🔴 Соединение разорвано';
                document.getElementById('status').style.color = '#f44336';
            };
        </script>
    </body>
    </html>
    """
