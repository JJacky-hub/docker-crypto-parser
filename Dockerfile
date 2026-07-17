FROM python:3.10-slim

WORKDIR /app

# Сначала копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем сам скрипт
COPY crypto.py .

# Команда по умолчанию для запуска FastAPI
CMD ["uvicorn", "crypto:app", "--host", "0.0.0.0", "--port", "8000"]
