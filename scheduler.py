import asyncio
from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource
from broker import broker
import tasks  # Импортируем модуль с задачами

# Создаем планировщик
scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)
