FROM python:3.12-slim AS builder

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /install /usr/local

RUN mkdir -p /app/logs /app/cookies/storage

COPY backend/requirements.txt .
COPY backend/app/ ./app/
COPY backend/tests/ ./tests/
COPY config/ ./config/
COPY database/ ./database/
COPY tasks/ ./tasks/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
