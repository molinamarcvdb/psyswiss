PORT ?= 8001
DATA_DIR ?= ./data
DB_FILE ?= psyswiss.db

.PHONY: setup dev run scrape searches clean

setup:
	./setup.sh

dev:
	DATA_DIR=$(DATA_DIR) DB_FILE=$(DB_FILE) DISABLE_SCHEDULER=1 uv run uvicorn app.main:app --reload --port $(PORT)

run:
	DATA_DIR=$(DATA_DIR) DB_FILE=$(DB_FILE) uv run uvicorn app.main:app --host 0.0.0.0 --port $(PORT)

scrape:
	DATA_DIR=$(DATA_DIR) DB_FILE=$(DB_FILE) uv run python -m app.cli scrape $(FORCE)

searches:
	DATA_DIR=$(DATA_DIR) DB_FILE=$(DB_FILE) uv run python -m app.cli searches

clean:
	rm -rf .venv __pycache__ app/__pycache__ $(DATA_DIR)/*.db
