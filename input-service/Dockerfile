# --- Stage 1: Builder ---
FROM python:3.12-slim as builder

# Build arguments for mirror configuration
ARG PIP_INDEX_URL=https://pypi.org/simple/
ARG PIP_TRUSTED_HOST=pypi.org

# Configure pip to use the specified index
ENV PIP_INDEX_URL=${PIP_INDEX_URL}
ENV PIP_TRUSTED_HOST=${PIP_TRUSTED_HOST}

WORKDIR /app

# Install poetry for dependency management
RUN pip install --no-cache-dir poetry

# Configure poetry to create venv in project directory
RUN poetry config virtualenvs.in-project true

# Configure poetry to use the same index as pip
RUN if [ "${PIP_INDEX_URL}" != "https://pypi.org/simple/" ]; then \
        poetry config repositories.tsinghua ${PIP_INDEX_URL%/simple/}/simple/ && \
        poetry config repositories.default ${PIP_INDEX_URL%/simple/}/simple/; \
    fi

# Copy the event bus framework first (the dependency)
COPY ./libs/event_bus_framework ./libs/event_bus_framework

# Copy only dependency files to leverage Docker layer caching
COPY ./input-service/pyproject.toml ./pyproject.toml

# Modify the path in pyproject.toml to match our copied structure
RUN sed -i 's|../libs/event_bus_framework|./libs/event_bus_framework|g' pyproject.toml

# Install only runtime dependencies (no dev) for the service into a
# virtual environment located at /.venv
RUN poetry install --no-interaction --no-ansi --without dev --no-root

# --- Stage 2: Final Image ---
FROM python:3.12-slim

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /home/appuser/app

# Create logs directory with proper permissions
RUN mkdir -p /home/appuser/app/logs && chown -R appuser:appuser /home/appuser/app/logs

USER appuser

# Copy the virtual environment from builder stage
COPY --from=builder /app/.venv ./.venv

# Ensure the virtualenv bin is first on PATH
ENV PATH="/home/appuser/app/.venv/bin:$PATH"

# Copy application source code only (no tests)
COPY --chown=appuser:appuser ./input-service/src ./src

# Copy shared libraries
COPY --chown=appuser:appuser ./libs ./libs

# Ensure libs are discoverable
ENV PYTHONPATH="/home/appuser/app/src:/home/appuser/app/libs/event_bus_framework/src:$PYTHONPATH"

# Expose service port (FastAPI default 8000)
EXPOSE 8000

# Start the application
CMD ["python", "-m", "input_service.main"] 