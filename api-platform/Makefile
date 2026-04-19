# Makefile for API Platform

.PHONY: help install dev test lint format clean docker-up docker-down db-init db-seed

# Default target
help:
	@echo "API Platform - Makefile Commands"
	@echo ""
	@echo "  install      Install dependencies"
	@echo "  dev          Install development dependencies"
	@echo "  test         Run tests"
	@echo "  lint         Run linters"
	@echo "  format       Format code"
	@echo "  clean        Clean cache files"
	@echo "  docker-up    Start Docker services"
	@echo "  docker-down  Stop Docker services"
	@echo "  db-init      Initialize database"
	@echo "  db-seed      Seed test data"

# Install dependencies
install:
	pip install -r requirements.txt

# Install development dependencies
dev:
	pip install -r requirements-dev.txt

# Run tests
test:
	pytest

# Run tests with coverage
test-cov:
	pytest --cov=src --cov-report=html --cov-report=term

# Run linters
lint:
	flake8 src/ tests/
	mypy src/
	pylint src/

# Format code
format:
	black src/ tests/
	isort src/ tests/

# Clean cache files
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov/
	rm -rf .coverage

# Docker commands
docker-up:
	cd docker && docker-compose up -d

docker-down:
	cd docker && docker-compose down

docker-build:
	cd docker && docker-compose build

# Database commands
db-init:
	python scripts/init_db.py

db-seed:
	python scripts/seed_data.py

db-reset:
	python scripts/init_db.py --drop
	python scripts/init_db.py
	python scripts/seed_data.py

# Run development server
run:
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Generate requirements
freeze:
	pip freeze > requirements.txt
