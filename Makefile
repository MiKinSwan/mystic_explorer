.PHONY: install api mine test lint

install:
	uv sync --extra lint

api:
	uv run uvicorn fast_api_app:fastapi_app --host 127.0.0.1 --port 8080

mine:
	uv run python -m app.pipeline.mine --states all --max-history-lookups-per-state 0

test:
	uv run python -m pytest tests/unit

lint:
	uv run ruff check . --fix
	uv run ruff format .
	uv run ty check .
