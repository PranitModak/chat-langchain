.PHONY: setup install-backend install-frontend ingest start-backend start-frontend start format lint test clean help

# Default target
help:
	@echo "Available commands:"
	@echo "  setup          - Complete setup (install dependencies, setup env)"
	@echo "  install-backend - Install Python dependencies with Poetry"
	@echo "  install-frontend - Install Node.js dependencies"
	@echo "  ingest         - Ingest documentation data (web scraping mode)"
	@echo "  ingest-sphinx  - Ingest documentation data (sphinx build mode)"
	@echo "  ingest-git     - Ingest documentation data (git access mode)"
	@echo "  start-backend  - Start the FastAPI backend server"
	@echo "  start-frontend - Start the Next.js frontend development server"
	@echo "  start          - Start both backend and frontend (requires tmux)"
	@echo "  format         - Format code with ruff"
	@echo "  lint           - Lint code with ruff"
	@echo "  test           - Run tests"
	@echo "  clean          - Clean up generated files"

# Complete setup
setup: install-backend install-frontend
	@echo "Setting up environment..."
	@if [ ! -f .env ]; then \
		cp env.example .env; \
		echo "Created .env file from env.example"; \
		echo "Please edit .env and add your API keys"; \
	else \
		echo ".env file already exists"; \
	fi
	@echo "Setup complete! Edit .env with your API keys and run 'make ingest'"

# Install backend dependencies
install-backend:
	@echo "Installing Python dependencies..."
	poetry install
	@echo "Backend dependencies installed"

# Install frontend dependencies
install-frontend:
	@echo "Installing Node.js dependencies..."
	cd frontend && npm install
	@echo "Frontend dependencies installed"

# Ingest documentation data
ingest:
	@echo "Ingesting documentation data (web scraping mode)..."
	poetry run python backend/ingest.py --mode web --wipe

ingest-sphinx:
	@echo "Ingesting documentation data (sphinx build mode)..."
	poetry run python backend/ingest.py --mode sphinx --wipe

ingest-git:
	@echo "Ingesting documentation data (git access mode)..."
	poetry run python backend/ingest.py --mode gitingest --wipe

# Start backend server
start-backend:
	@echo "Starting backend server..."
	poetry run python backend/main.py

# Start frontend development server
start-frontend:
	@echo "Starting frontend development server..."
	cd frontend && npm run dev

# Start both servers (requires tmux)
start:
	@if command -v tmux >/dev/null 2>&1; then \
		tmux new-session -d -s chat-langchain; \
		tmux split-window -h; \
		tmux send-keys -t 0 "make start-backend" C-m; \
		tmux send-keys -t 1 "make start-frontend" C-m; \
		tmux attach-session -t chat-langchain; \
	else \
		echo "tmux not found. Please install tmux or run 'make start-backend' and 'make start-frontend' in separate terminals"; \
	fi

# Code formatting
format:
	poetry run ruff format .
	poetry run ruff --select I --fix .

# Code linting
lint:
	poetry run ruff .
	poetry run ruff format . --diff
	poetry run ruff --select I .

# Run tests
test:
	@echo "Running backend tests..."
	poetry run pytest backend/tests/
	@echo "Running frontend tests..."
	cd frontend && npm test

# Clean up generated files
clean:
	@echo "Cleaning up generated files..."
	rm -rf chroma_db/
	rm -rf frontend/.next/
	rm -rf frontend/node_modules/
	rm -rf __pycache__/
	rm -rf backend/__pycache__/
	rm -rf backend/*/__pycache__/
	rm -rf .pytest_cache/
	@echo "Cleanup complete"

