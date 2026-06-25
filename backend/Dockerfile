FROM python:3.12-slim AS builder

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /install /usr/local

RUN mkdir -p /app/logs /app/scraper/cookies/storage /app/run_data

COPY backend/app/ ./app/
COPY scraper/   ./scraper/

EXPOSE 18642

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "18642"]
