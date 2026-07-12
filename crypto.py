import requests
import time
import psycopg2
import os

print("🚀 Запуск крипто-парсера в режиме интеграции с PostgreSQL...")

# Извлекаем настройки подключения из переменных окружения Docker Compose
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_NAME = os.getenv("DB_NAME", "crypto_db")
DB_USER = os.getenv("DB_USER", "postgres_user")
DB_PASS = os.getenv("DB_PASS", "super_password")

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
url = 'https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT'

# Фаза инициализации: ждем, пока Postgres поднимется и создаем таблицу
while True:
    try:
        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cursor = conn.cursor()
        
        # Создаем таблицу для истории курсов, если её не существует
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS btc_history (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                price NUMERIC(12, 2) NOT NULL
            );
        """)
        conn.commit()
        print("✅ Успешно подключились к PostgreSQL. Таблица btc_history готова.")
        break
    except psycopg2.OperationalError:
        print("⏳ База данных еще загружается, ожидаем 3 секунды...")
        time.sleep(3)

# Основной цикл мониторинга
while True:
    try:
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        price = float(data['price'])
        
        print(f"📈 [PostgreSQL] Отправка в БД: Курс BTC = ${price:,.2f}")
        
        # Запись данных в Postgres (NOW() автоматически подставит текущее время базы)
        cursor.execute(
            "INSERT INTO btc_history (timestamp, price) VALUES (NOW(), %s);",
            (price,)
        )
        conn.commit()
        
    except Exception as e:
        print(f"❌ Ошибка во время работы: {e}")
        # Попытка восстановить соединение, если БД моргнула
        try:
            conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
            cursor = conn.cursor()
        except:
            pass
            
    time.sleep(10)
