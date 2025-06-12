# ==============================================================================
# Monorepo Makefile (refactored to follow specification V3.0)
# -----------------------------------------------------------------------------
# This Makefile acts as the single entry-point for local development and CI/CD.
# It intentionally limits itself to a concise set of high-value targets.
# ==============================================================================

.PHONY: help lint format test-unit test-integration-ab test-integration-ac \
       test-integration test-e2e test-all clean

# List all microservice directories here. When new services are added, update
# this variable only.
SERVICES := input-service

# Detect poetry automatically
POETRY := $(shell command -v poetry 2> /dev/null)

# Mirror configuration for Chinese users
# Usage: make test-integration-input USE_CHINA_MIRROR=true
USE_CHINA_MIRROR ?= false
ifeq ($(USE_CHINA_MIRROR),true)
    PIP_INDEX_URL := https://pypi.tuna.tsinghua.edu.cn/simple/
    PIP_TRUSTED_HOST := pypi.tuna.tsinghua.edu.cn
    DOCKER_BUILD_ARGS := --build-arg PIP_INDEX_URL=$(PIP_INDEX_URL) --build-arg PIP_TRUSTED_HOST=$(PIP_TRUSTED_HOST)
else
    DOCKER_BUILD_ARGS :=
endif

# -----------------------------------------------------------------------------
# Default target: show help
# -----------------------------------------------------------------------------
help: ## Display this help message
	@echo "Usage: make <target> [USE_CHINA_MIRROR=true]"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Options:"
	@echo "  USE_CHINA_MIRROR=true    Use Tsinghua mirror for pip/poetry (faster in China)"

# -----------------------------------------------------------------------------
# Development helper tasks
# -----------------------------------------------------------------------------

lint: ## (all) Run the ruff linter across the repo
	@echo "--- Running ruff linter ---"
	$(POETRY) run ruff check .

format: ## (all) Format code with black & ruff
	@echo "--- Formatting code ---"
	$(POETRY) run black .
	$(POETRY) run ruff format .

# -----------------------------------------------------------------------------
# Testing tasks
# -----------------------------------------------------------------------------

# SERVICE variable allows scoping to a single service (default = all)
SERVICE ?= $(SERVICES)

test-unit: ## (unit) Run unit tests for the given service(s)
	@for service in $(SERVICE); do \
		echo "--- Running unit tests for $$service ---"; \
		(cd ./$$service && $(POETRY) run pytest tests/unit); \
	 done

test-integration-ab: ## (integration) Run integration scenario A<->B
	@echo "--- Running integration tests for A<->B ---"
	(cd ./tests/integration && docker-compose --profile test-ab up --build --abort-on-container-exit --exit-code-from test-runner-ab)

test-integration-ac: ## (integration) Run integration scenario A<->C
	@echo "--- Running integration tests for A<->C ---"
	(cd ./tests/integration && docker-compose --profile test-ac up --build --abort-on-container-exit --exit-code-from test-runner-ac)

test-integration-input: ## (integration) Run integration tests for Input Service
	@echo "--- Running integration tests for input-service ---"
ifeq ($(USE_CHINA_MIRROR),true)
	@echo "--- Using Tsinghua mirror for faster downloads ---"
	(cd ./tests/integration && DOCKER_BUILDKIT=1 docker compose --profile test-input build $(DOCKER_BUILD_ARGS))
	(cd ./tests/integration && docker compose --profile test-input up --abort-on-container-exit --exit-code-from test-runner-input)
else
	(cd ./tests/integration && docker compose --profile test-input up --build --abort-on-container-exit --exit-code-from test-runner-input)
endif

test-integration: test-integration-ab test-integration-ac test-integration-input ## (integration) Run all integration tests
	@echo "--- All integration tests passed ---"

test-e2e: ## (e2e) Run end-to-end tests
	@echo "--- Running end-to-end tests ---"
	(cd ./tests/e2e && docker-compose up --build --abort-on-container-exit --exit-code-from test-runner)

test-all: test-unit test-integration ## (all) Run unit + integration tests
	@echo "--- All essential tests passed ---"

# -----------------------------------------------------------------------------
# Utility tasks
# -----------------------------------------------------------------------------

clean: ## Remove dangling Docker artifacts
	@echo "Cleaning up Docker images & containers"
	docker image prune -f
	docker system prune -f

# 构建所有服务
# 删除至文件末尾 