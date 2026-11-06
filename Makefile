-include .env
export

PY_VERSION := $(shell cat .python-version)
include temporal/version.env

.PHONY: build-pyenv install run-pre-commit test test_e2e test_e2e_integrated test_e2e_mocked run_frontend run_backend run_worker run run_watch stop generate_api_types

build-pyenv:
	uv python install ${PY_VERSION}

install:
	cd frontend && npm install
	brew install ffmpeg
	uv sync
	uv run pre-commit install

run-pre-commit:
	uv run pre-commit run --all-files

# A local CA bundle supports networks that inspect HTTPS; never committed.
CA_BUNDLE = $(CURDIR)/certs/host-ca-bundle.pem
CA_SH = if [ -f "$(CA_BUNDLE)" ]; then \
	REQUESTS_CA_BUNDLE="$(CA_BUNDLE)"; SSL_CERT_FILE="$(CA_BUNDLE)"; \
	AWS_CA_BUNDLE="$(CA_BUNDLE)"; CURL_CA_BUNDLE="$(CA_BUNDLE)"; \
	GRPC_DEFAULT_SSL_ROOTS_FILE_PATH="$(CA_BUNDLE)"; \
	fi;

# Shell sourcing avoids make retaining literal quotes in JSON settings.
ENV_SH = set -a; if [ -f .env ]; then . ./.env; fi; $(CA_SH) set +a;

# Requires local Compose Postgres/MiniStack; paid APIs are disabled.
test:
	$(ENV_SH) ALLOW_TESTS_TO_ACCESS_PAID_APIS=0 uv run pytest tests/

test_e2e:
	$(ENV_SH) uv run pytest tests/

test_e2e_integrated:
	cd frontend && npm run test:e2e:integrated

test_e2e_mocked:
	cd frontend && npm run test:e2e:mocked

run_frontend:
	cd frontend && npm run dev

run_backend:
	uv run uvicorn backend.main:app --reload --port 8080

run_worker:
	uv run python worker/temporal_worker.py

run:
	TEMPORAL_VERSION=$(TEMPORAL_VERSION) docker compose up --build -d --wait

run_watch:
	TEMPORAL_VERSION=$(TEMPORAL_VERSION) docker compose up --watch

stop:
	docker compose down

generate_api_types:
	cd frontend && npm run openapi-ts
