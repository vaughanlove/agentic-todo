.PHONY: help install test lint format run clean setup

help:
	@echo "Agentic Todo - Makefile Commands"
	@echo ""
	@echo "  make setup      - Complete setup (venv, install, config)"
	@echo "  make install    - Install dependencies"
	@echo "  make test       - Run tests"
	@echo "  make test-cov   - Run tests with coverage"
	@echo "  make lint       - Run linters"
	@echo "  make format     - Format code"
	@echo "  make run        - Run application"
	@echo "  make clean      - Clean build artifacts"
	@echo ""

setup: venv install config
	@echo "Setup complete! Edit .env and config.yaml, then run: make run"

venv:
	@echo "Creating virtual environment..."
	python3 -m venv venv
	@echo "Virtual environment created. Activate with: source venv/bin/activate"

install:
	@echo "Installing dependencies..."
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt
	./venv/bin/pip install -e .
	@echo "Dependencies installed."

config:
	@echo "Setting up configuration files..."
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env - please edit it"; fi
	@if [ ! -f config.yaml ]; then cp config.yaml.example config.yaml; echo "Created config.yaml - please edit it"; fi

test:
	@echo "Running tests..."
	./venv/bin/pytest -v

test-cov:
	@echo "Running tests with coverage..."
	./venv/bin/pytest --cov=src --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/index.html"

lint:
	@echo "Running linters..."
	./venv/bin/ruff check src/ tests/
	./venv/bin/mypy src/

format:
	@echo "Formatting code..."
	./venv/bin/black src/ tests/
	./venv/bin/ruff check --fix src/ tests/

run:
	@echo "Starting Agentic Todo..."
	./venv/bin/python -m src.main

clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "Clean complete."

logs:
	@echo "Tailing application logs..."
	tail -f logs/app.log

stats:
	@echo "Code statistics..."
	@find src -name "*.py" | xargs wc -l | tail -1
	@echo ""
	@echo "Test coverage:"
	@./venv/bin/pytest --cov=src --cov-report=term-missing | tail -20
