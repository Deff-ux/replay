.PHONY: dev backend frontend docker-build
backend:
	uvicorn backend.app.main:app --host 0.0.0.0 --port 8446 --reload
frontend:
	npm --prefix frontend run dev
docker-build:
	docker build -t replay:latest -f docker/Dockerfile .
