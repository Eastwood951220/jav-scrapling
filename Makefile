.PHONY: start stop restart logs status build

start:
	docker compose up -d
	@echo "Services started."
	@echo "  Frontend: http://localhost"
	@echo "  Backend:  http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/docs"

stop:
	docker compose down

restart:
	docker compose down
	docker compose up -d

logs:
	docker compose logs -f

status:
	docker compose ps

build:
	docker compose build --no-cache

dev-backend:
	cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

dev-frontend:
	cd frontend && npm run dev

dev:
	@echo "Starting backend (port 8000) and frontend (port 5173)..."
	@cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload & \
	cd frontend && npm run dev
