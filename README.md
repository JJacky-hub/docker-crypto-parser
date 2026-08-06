# 🚀 Async Crypto Price Tracker & API

A highly scalable, fully asynchronous microservice application that tracks real-time cryptocurrency prices and serves them via a REST API and WebSockets.

This project demonstrates a decoupled backend architecture where background tasks and the main web server operate independently, communicating via Redis.

## ✨ Key Features

* **Microservice Architecture:** Web API, background workers, and task schedulers run in isolated Docker containers.
* **Fully Asynchronous:** Built with Python's `asyncio` to handle concurrent operations efficiently.
* **Background Workers:** Utilizes `Taskiq` and `Redis` to fetch data from the MEXC Exchange API without blocking the main event loop.
* **Automated Scheduling:** A dedicated scheduler container triggers price parsing jobs strictly every 10 seconds.
* **Async Database Operations:** Employs `SQLAlchemy` (with `asyncpg`) for non-blocking PostgreSQL queries.
* **Dockerized Stack:** Production-ready `docker-compose.yml` that orchestrates FastAPI, Taskiq Worker, Taskiq Scheduler, Redis, and PostgreSQL.

## 🛠️ Tech Stack

* **Framework:** FastAPI
* **Background Tasks & Message Broker:** Taskiq, Redis
* **Database & ORM:** PostgreSQL, SQLAlchemy, asyncpg, Alembic
* **Infrastructure:** Docker, Docker Compose, Nginx

## 🚀 Quick Start (Run Locally)

Prerequisites: Make sure you have [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/) installed.

1. Clone the repository:
```bash
git clone https://github.com/JJacky-hub/docker-crypto-parser.git
cd docker-crypto-parser
```

2. Copy the example environment variables:
```bash
cp .env.example .env
```

3. Build and start the services:
```bash
docker compose up -d --build
```

4. Access the API:
* **Latest Prices Endpoint:** https://crypt0-parser.duckdns.org/api/prices/latest
