FROM python:3.10-slim

RUN pip install --no-cache-dir requests psycopg2-binary

COPY crypto.py /app/crypto.py

CMD ["python", "/app/crypto.py"]
