.PHONY: help install run-api run-dashboard test lint format typecheck migrate scrape clean docker-up docker-down docker-build

help:
	@echo "Murim Knowledge Base — Makefile"
	@echo ""
	@echo "Uso: make <target>"
	@echo ""
	@echo "────────────────────────────────────────────"
	@echo " Desenvolvimento"
	@echo "────────────────────────────────────────────"
	@echo "  install        Instalar dependencias via pip"
	@echo "  run-api        Subir API (uvicorn) na porta 8000"
	@echo "  run-dashboard  Subir Dashboard (streamlit) na porta 8501"
	@echo "  test           Rodar todos os testes via pytest"
	@echo "  lint           Rodar ruff (lint)"
	@echo "  format         Rodar ruff (format)"
	@echo "  typecheck      Rodar mypy"
	@echo "  scrape         Executar scrape manual"
	@echo ""
	@echo "────────────────────────────────────────────"
	@echo " Database"
	@echo "────────────────────────────────────────────"
	@echo "  migrate        Rodar migrations Alembic"
	@echo "  downgrade      Reverter ultima migration"
	@echo ""
	@echo "────────────────────────────────────────────"
	@echo " Docker"
	@echo "────────────────────────────────────────────"
	@echo "  docker-build   Build imagens Docker"
	@echo "  docker-up      Subir servicos (Postgres + API + Dashboard)"
	@echo "  docker-down    Derrubar servicos"
	@echo ""
	@echo "────────────────────────────────────────────"
	@echo " Utilidades"
	@echo "────────────────────────────────────────────"
	@echo "  clean          Remover __pycache__ e .pyc"
	@echo "  all            Rodar install, lint, typecheck, test"

install:
	pip install -r requirements.txt

run-api:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-dashboard:
	streamlit run app/dashboard/main.py

migrate:
	alembic upgrade head

downgrade:
	alembic downgrade -1

test:
	pytest tests/ -v

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy app/

scrape:
	@echo "Use POST /api/v1/scrape ou configure via .env"

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true

all: install lint typecheck test