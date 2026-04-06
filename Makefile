.PHONY: help install install-dev run-api run-dashboard seed lint test test-cov docker-build docker-up docker-down clean

help:  ## Show this help menu
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' Makefile | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install production dependencies
	pip install -r requirements.txt

install-dev:  ## Install dev + test dependencies
	pip install -r requirements-dev.txt

run-api:  ## Start the FastAPI backend (port 8000)
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-dashboard:  ## Start the Streamlit dashboard (port 8501)
	streamlit run dashboard/app.py --server.port 8501

seed:  ## Seed sample customers, tickets, and knowledge base
	python seed_data.py

lint:  ## Run ruff linter
	ruff check app/ tests/ dashboard/ seed_data.py

test:  ## Run all unit tests
	pytest tests/ -v

test-cov:  ## Run tests with coverage report
	pytest tests/ -v --cov=app --cov-report=html

docker-build:  ## Build Docker images
	docker compose build

docker-up:  ## Start all services with Docker Compose
	docker compose up -d

docker-down:  ## Stop all services
	docker compose down

docker-logs:  ## Tail Docker logs
	docker compose logs -f

clean:  ## Remove generated files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
	find . -name "*.pyc" -delete 2>/dev/null; \
	rm -rf .pytest_cache .ruff_cache htmlcov .coverage; \
	echo "Cleaned."
