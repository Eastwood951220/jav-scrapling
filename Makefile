.PHONY: start stop restart logs status build

start:
	docker compose up -d
	@echo "Services started."
	@echo "  Frontend: http://localhost:18643"
	@echo "  Backend:  http://localhost:18642"
	@echo "  API Docs: http://localhost:18642/docs"

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
	cd backend && uvicorn app.main:app --host 0.0.0.0 --port 18642 --reload

dev-frontend:
	cd frontend && npm run dev

dev:
	@echo "Starting backend (port 18642) and frontend (port 5173)..."
	@cd backend && uvicorn app.main:app --host 0.0.0.0 --port 18642 --reload & \
	cd frontend && npm run dev
