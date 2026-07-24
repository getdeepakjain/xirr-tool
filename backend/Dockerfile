# FastAPI backend container. Works on Fly.io, Railway, Render (Docker), etc.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Default SQLite location. Mount a persistent volume at /data in production so
# the database survives restarts/redeploys (override DATABASE_URL to use Postgres).
ENV DATABASE_URL=sqlite:////data/portfolio.sqlite3
RUN mkdir -p /data

EXPOSE 8000

# Hosts inject $PORT; fall back to 8000 for plain `docker run`.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
