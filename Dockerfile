FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app

# CMD ["bash", "-lc", "DB_URL=${DATABASE_URL:-postgresql://postgres:postgres@db:5432/raffaello}; DB_URL=${DB_URL//+psycopg/}; until python -c \"import psycopg; psycopg.connect('$DB_URL')\" 2>/dev/null; do echo 'Waiting for database...'; sleep 1; done && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
CMD ["bash", "-lc", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
