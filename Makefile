.PHONY: compose-up compose-down compose-config runner-install runner-start legacy-backend legacy-frontend legacy-docker-build

compose-up:
	cd docker && docker compose up -d --build
compose-down:
	cd docker && docker compose down
compose-config:
	cd docker && docker compose config
runner-install:
	npm --prefix playwright-runner install
runner-start:
	npm --prefix playwright-runner start
legacy-backend:
	uvicorn backend.app.main:app --host 0.0.0.0 --port 8446 --reload
legacy-frontend:
	npm --prefix frontend run dev
legacy-docker-build:
	docker build -t replay-legacy:latest -f docker/Dockerfile .
