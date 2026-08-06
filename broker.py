import os
from taskiq_redis import ListQueueBroker

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Настраиваем вечное удержание соединения (keepalive)
broker = ListQueueBroker(
    url=REDIS_URL,
    socket_timeout=None,
    socket_keepalive=True,
)
