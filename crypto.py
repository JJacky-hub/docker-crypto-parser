import os
import asyncio
from datetime import datetime
from typing import List

from fastapi import FastAPI, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
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

class CryptoPrice(Base):
    __tablename__ = "crypto_prices"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    price_usd = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Crypto Analytics Platform", version="3.0")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 2. Менеджер WebSocket-подключений
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

# 3. Фоновый воркер с рассылкой по WebSockets
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
                    
                    # Мгновенно рассылаем новые цены всем подключенным клиентам по WebSockets!
                    current_time = datetime.now().strftime('%H:%M:%S')
                    await manager.broadcast({"time": current_time, "prices": saved_dict})
                    print(f"[{current_time}] Трансляция цен в WebSocket: {saved_dict}", flush=True)
        except Exception as e:
            print(f"[WORKER ERROR] {e}", flush=True)
            
        await asyncio.sleep(15)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(fetch_crypto_prices())

# 4. WebSocket эндпоинт
@app.websocket("/ws/prices")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # Держим сокет открытым
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# 5. Веб-Дашборд с Chart.js
@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard():
    return """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Crypto Real-time Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body { font-family: Arial, sans-serif; background: #121212; color: #fff; text-align: center; margin: 20px; }
            .container { width: 80%; margin: 0 auto; background: #1e1e1e; padding: 20px; border-radius: 12px; }
            .status { font-weight: bold; margin-bottom: 20px; color: #4caf50; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>📈 Crypto Real-time WebSocket Dashboard</h2>
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

            // Подключаемся к нашему WebSocket
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/prices`);

            ws.onopen = () => {
                document.getElementById('status').innerText = '🟢 WebSocket Соединение установлено (Live Data)';
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                const time = data.time;
                const prices = data.prices;

                // Добавляем новые точки на график
                cryptoChart.data.labels.push(time);
                cryptoChart.data.datasets[0].data.push(prices.BTCUSDT);
                cryptoChart.data.datasets[1].data.push(prices.ETHUSDT);
                cryptoChart.data.datasets[2].data.push(prices.SOLUSDT);

                // Ограничиваем график последними 20 измерениями
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
