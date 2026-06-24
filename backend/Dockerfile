FROM python:3.12-slim AS builder

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /install /usr/local

RUN mkdir -p /app/logs /app/cookies/storage

COPY backend/app/ ./app/
COPY config/    ./config/
COPY cookies/   ./cookies/
COPY core/      ./core/
COPY database/  ./database/
COPY fetchers/  ./fetchers/
COPY pipelines/ ./pipelines/
COPY services/  ./services/
COPY spiders/   ./spiders/
COPY tasks/     ./tasks/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
