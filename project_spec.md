### **Python Microservices Project Refactoring and Management Specification**

**Version**: 3.0 (Final)
**Date**: June 11, 2025

#### **Introduction**

This specification aims to provide a clear and complete set of instructions for an AI Agent to refactor an existing Python microservices project into a standardized, manageable, testable, and container-ready monorepo structure.

---

### **I. Overall Project Structure**

The project will adopt a monorepo model, with all microservices and related code residing in a single Git repository. The top-level directory should clearly separate service code from cross-service testing code.

```
my_project/
├── .dockerignore        # Files to be ignored by Docker builds
├── .gitignore           # Files to be ignored by Git
├── Makefile             # The single entry point for all automated tasks (for CI/CD and local development)
├── docker-compose.yml   # [Optional] For launching all services together for local integration
├── pyproject.toml       # [Root-level] For managing development tools for the entire project
├── poetry.lock          # [Root-level] Lock file for development tools
├── tests/               # Contains all cross-service testing code
│   ├── integration/     # Integration tests
│   │   ├── docker-compose.yml              # Defines all services and test scenarios (profiles)
│   │   ├── Dockerfile.test_runner        # Dockerfile for the test runner
│   │   ├── test_ab_interaction.py        # Test script for scenario one
│   │   └── test_ac_interaction.py        # Test script for scenario two
│   └── e2e/             # End-to-end tests
│       └── ...
├── service_a/           # Microservice A
│   ├── Dockerfile         # Containerization config for Service A
│   ├── docker-compose.dev.yml # Local development environment for Service A
│   ├── pyproject.toml     # [Service-level] Manages runtime dependencies for Service A only
│   ├── poetry.lock      # [Service-level] Lock file for Service A
│   ├── tests/
│   │   └── unit/        # Unit tests for Service A
│   │       └── test_*.py
│   └── src/             # Source code for Service A
└── service_b/           # Microservice B
    ├── ...              # Same structure as Service A
```

---

### **II. Dependency Management Specification (Poetry)**

The project will use `Poetry` as the dependency management tool, following a two-level `pyproject.toml` model.

**1. Service-Level `pyproject.toml`**
* **Responsibility**: To strictly manage the **runtime** dependencies required for that specific microservice.
* **Principles**:
    * **Isolation**: The dependencies of each microservice are independent and should not interfere with others.
    * **Minimality**: It should only contain packages essential for running the service, not for testing or linting.
* **Example (`/service_a/pyproject.toml`)**:
    ```toml
    [tool.poetry]
    name = "service-a"
    version = "0.1.0"
    description = "Handles order processing."
    authors = ["Your Team <team@example.com>"]

    [tool.poetry.dependencies]
    python = "^3.10"
    flask = "^3.0"
    redis = "^5.0"
    ```

**2. Root-Level `pyproject.toml`**
* **Responsibility**: To uniformly manage the tools used during **development and CI/CD** across the entire project.
* **Principles**:
    * **Development-Only**: All dependencies should be defined under `[tool.poetry.group.dev.dependencies]`.
    * **Global Consistency**: Ensure all developers and automation pipelines use a consistent set of versioned tools.
* **Example (`/pyproject.toml`)**:
    ```toml
    [tool.poetry]
    name = "my-project-devtools"
    version = "0.1.0"
    description = "Development tools for the monorepo."
    authors = ["Your Team <team@example.com>"]

    [tool.poetry.group.dev.dependencies]
    python = "^3.10"
    black = "^24.0"
    ruff = "^0.4.0"
    pytest = "^8.0"
    requests = "^2.31" # For integration test scripts
    ```

---

### **III. Containerization Specification (Docker)**

#### **3.1. `Dockerfile` Best Practices**

Each microservice must have a `Dockerfile` that uses **multi-stage builds** to create small and secure production images.

**`/service_a/Dockerfile` Template:**
```dockerfile
# --- Stage 1: Builder ---
# Use a full Python image as the build environment
FROM python:3.10-slim-bookworm as builder

WORKDIR /app

# Install poetry
RUN pip install poetry

# Copy only the dependency definition files to leverage Docker's layer cache
COPY poetry.lock pyproject.toml ./

# Use poetry to install dependencies into a virtual environment
# --no-root: Does not install the project itself, only dependencies
# --without dev: Does not install development dependencies
RUN poetry install --no-interaction --no-ansi --without dev --no-root

# --- Stage 2: Final Image ---
# Use a lighter base image for the final product
FROM python:3.10-slim-bookworm

# Create a non-root user to run the application for better security
RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /home/appuser/app
USER appuser

# Copy the virtual environment created in the builder stage
COPY --from=builder --chown=appuser:appuser /app/.venv ./.venv

# Add the virtual environment's bin directory to the PATH
ENV PATH="/home/appuser/app/.venv/bin:$PATH"

# Copy the application source code
COPY --chown=appuser:appuser ./src .

# Expose the application port
EXPOSE 5000

# Command to run when the container starts
CMD ["flask", "run", "--host=0.0.0.0"]
```

#### **3.2. Local Development Environment (`docker-compose.dev.yml`)**

For easy local development of a single service, each service directory should contain a `docker-compose.dev.yml`. Its key feature is using a **bind mount** for live code reloading.

**`/service_a/docker-compose.dev.yml` Example:**
```yaml
version: '3.9'

services:
  service-a:
    build: .
    ports:
      - "5001:5000" # Map container port 5000 to host port 5001
    volumes:
      - ./src:/home/appuser/app # Mount local src directory into the container for live updates
    environment:
      - FLASK_ENV=development
```
**Usage**: From within the `/service_a` directory, run `docker-compose -f docker-compose.dev.yml up`.

#### **3.3. Testing Environments (Unified `docker-compose.yml` with Profiles)**

Integration and E2E tests will use a single, unified `docker-compose.yml` file located in `/tests/integration/`, leveraging `profiles` to manage test scenarios.

**`/tests/integration/docker-compose.yml` Example:**
```yaml
version: '3.9'

services:
  service-a:
    build: ../../service_a
    profiles: ["test-ab", "test-ac"]

  service-b:
    build: ../../service_b
    profiles: ["test-ab"]

  service-c:
    build: ../../service_c
    profiles: ["test-ac"]

  test-runner-ab:
    build:
      context: ../.. 
      dockerfile: ./tests/integration/Dockerfile.test_runner
    profiles: ["test-ab"]
    depends_on: [service-a, service-b]
    command: pytest test_ab_interaction.py

  test-runner-ac:
    build:
      context: ../..
      dockerfile: ./tests/integration/Dockerfile.test_runner
    profiles: ["test-ac"]
    depends_on: [service-a, service-c]
    command: pytest test_ac_interaction.py
```

**`/tests/integration/Dockerfile.test_runner` Example:**
```dockerfile
FROM python:3.10-slim-bookworm
WORKDIR /app
RUN pip install poetry
COPY pyproject.toml poetry.lock ./
# Install all development dependencies, including pytest, requests, etc.
RUN poetry install --no-interaction --no-ansi --only dev
COPY . .
```

---

### **IV. Testing Strategy and Organization**

A three-tiered testing strategy of **Unit, Integration, and End-to-End tests** will be adopted.

**1. Unit Tests**
* **Goal**: To test a single function, class, or module in isolation.
* **Location**: Within each service at `/<service_name>/tests/unit/`.
* **Key Points**: All external dependencies (databases, network calls, etc.) **must** be mocked. They should be fast and cover core business logic.

**2. Integration Tests**
* **Goal**: To verify the collaboration and communication contracts between a small group of real microservices.
* **Location**: In the root `/tests/integration/` directory.
* **Key Points**:
    * Uses the unified `docker-compose.yml` with `profiles` to launch specific subsets of services.
    * A dedicated `test-runner` service within the compose file executes test scripts that make API calls and verify interactions between the live services.
    * Triggered via `Makefile` targets like `make test-integration-ab`.

**3. End-to-End (E2E) Tests**
* **Goal**: To simulate a real user journey and verify that a complete business workflow succeeds.
* **Location**: In the root `/tests/e2e/` directory.
* **Key Points**:
    * Runs against a fully deployed environment (like staging) where all relevant services are running.
    * Tests should be minimal in number, covering only the most critical business scenarios.

---

### **V. Automation Workflow Specification (Makefile)**

A root `Makefile` serves as the single entry point for all automated tasks.

```makefile
# Makefile in project root
.PHONY: help test-unit test-integration-ab test-integration-ac test-integration test-e2e clean lint format test-all

# Define all microservice directories
SERVICES := service_a service_b

# Find the poetry command automatically
POETRY := $(shell command -v poetry 2> /dev/null)

# ==============================================================================
# Default Target: Print Help Information
# ==============================================================================
help: ## Display this help message
	@echo "Usage: make <target>"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}'

# ==============================================================================
# Development Helper Tasks
# ==============================================================================
lint: ## (all) Run the linter on all service code
	@echo "--- Running linter for all services ---"
	$(POETRY) run ruff check .

format: ## (all) Format all service code
	@echo "--- Formatting code for all services ---"
	$(POETRY) run black .
	$(POETRY) run ruff format .

# ==============================================================================
# Testing Tasks
# ==============================================================================

# The SERVICE variable allows targeting a single service, defaults to all
# Example: make test-unit
# Example: make test-unit SERVICE=service_a
SERVICE ?= $(SERVICES)

test-unit: ## (unit) Run unit tests for a specific service (or all)
	@for service in $(SERVICE); do \
		echo "--- Running unit tests for $$service ---"; \
		(cd ./$$service && $(POETRY) run pytest tests/unit); \
	done

test-integration-ab: ## (integration) Run integration tests for Service A <-> B
	@echo "--- Running integration tests for Service A <-> B ---"
	(cd ./tests/integration && docker-compose --profile test-ab up --build --abort-on-container-exit --exit-code-from test-runner-ab)

test-integration-ac: ## (integration) Run integration tests for Service A <-> C
	@echo "--- Running integration tests for Service A <-> C ---"
	(cd ./tests/integration && docker-compose --profile test-ac up --build --abort-on-container-exit --exit-code-from test-runner-ac)

test-integration: test-integration-ab test-integration-ac ## (integration) Run all defined integration test scenarios
	@echo "--- All integration tests passed ---"

test-e2e: ## (e2e) Run end-to-end tests
	@echo "--- Running End-to-End tests ---"
	(cd ./tests/e2e && docker-compose up --build --abort-on-container-exit --exit-code-from test-runner)

test-all: test-unit test-integration ## (all) Run all unit and integration tests
	@echo "--- All essential tests passed ---"
```

### **VI. CI/CD Guiding Principles**

1.  **On Pull Request**: The pipeline must run `make lint` and `make test-unit`.
2.  **On Merge to main/develop**: The pipeline should run `make test-integration` to execute all integration test scenarios.
3.  **Build Production Images**: In the pipeline, navigate to each service directory and run `docker build -t my-registry/service-name:tag .`.
4.  **After Deploying to Staging**: The pipeline can trigger `make test-e2e`.
5.  **Deploy to Production**: Deploy the tested and verified images to the production environment.