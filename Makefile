.PHONY: up down build logs test evaluate validate-models

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

test:
	docker compose exec backend pytest

evaluate:
	docker compose exec backend python -m evaluation.run

validate-models:
	docker compose exec backend python -m scripts.validate_models
