import os
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import CryptoPrice

app = FastAPI(title="Crypto Parser API")

@app.get("/")
async def root():
    return {"status": "ok", "message": "Crypto Parser API is running"}

@app.get("/api/prices/latest")
async def get_latest_prices(db: AsyncSession = Depends(get_db)):
    """Получить последние цены по всем монетам"""
    result = await db.execute(
        select(CryptoPrice).order_by(CryptoPrice.timestamp.desc()).limit(10)
    )
    prices = result.scalars().all()
    return prices

@app.websocket("/ws/prices")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket для real-time котировок"""
    await websocket.accept()
    try:
        while True:
            # Здесь логика отправки свежих цен из Redis Pub/Sub или БД
            data = await websocket.receive_text()
            await websocket.send_text(f"Message received: {data}")
    except WebSocketDisconnect:
        print("Client disconnected")
