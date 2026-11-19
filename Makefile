.PHONY: up up-core down logs test

up:
	docker compose --profile judge up --build -d --wait

up-core:
	docker compose up --build -d --wait

down:
	docker compose down

logs:
	docker compose logs -f

test:
	cd backend && pytest tests ../judge/tests
	cd frontend && npm run typecheck && npm run build && npm test
