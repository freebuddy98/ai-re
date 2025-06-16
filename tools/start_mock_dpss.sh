#!/bin/bash

# Start Mock DPSS Service
# 
# This script starts the Mock DPSS service with proper environment setup.
# It can be used for development and testing of the NLU service.

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Starting Mock DPSS Service..."
echo "Project root: $PROJECT_ROOT"

# Change to project root
cd "$PROJECT_ROOT"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Error: Virtual environment not found at .venv"
    echo "Please run 'poetry install' first to create the virtual environment"
    exit 1
fi

# Check if required dependencies are installed
if ! .venv/bin/python -c "import fastapi, uvicorn, yaml" 2>/dev/null; then
    echo "Installing required dependencies..."
    .venv/bin/pip install fastapi uvicorn pyyaml
fi

# Default configuration
HOST="${MOCK_DPSS_HOST:-0.0.0.0}"
PORT="${MOCK_DPSS_PORT:-8080}"
DATA_FILE="${MOCK_DPSS_DATA_FILE:-tools/mock_dpss_data.yml}"
RELOAD="${MOCK_DPSS_RELOAD:-false}"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --data-file)
            DATA_FILE="$2"
            shift 2
            ;;
        --reload)
            RELOAD="true"
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --host HOST         Host to bind to (default: 0.0.0.0)"
            echo "  --port PORT         Port to bind to (default: 8080)"
            echo "  --data-file FILE    Path to mock data file (default: tools/mock_dpss_data.yml)"
            echo "  --reload            Enable auto-reload for development"
            echo "  --help              Show this help message"
            echo ""
            echo "Environment variables:"
            echo "  MOCK_DPSS_HOST      Host to bind to"
            echo "  MOCK_DPSS_PORT      Port to bind to"
            echo "  MOCK_DPSS_DATA_FILE Path to mock data file"
            echo "  MOCK_DPSS_RELOAD    Enable auto-reload (true/false)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Build command arguments
ARGS=(
    "--host" "$HOST"
    "--port" "$PORT"
    "--data-file" "$DATA_FILE"
)

if [ "$RELOAD" = "true" ]; then
    ARGS+=("--reload")
fi

echo "Configuration:"
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Data file: $DATA_FILE"
echo "  Auto-reload: $RELOAD"
echo ""

# Check if port is already in use
if netstat -tlnp 2>/dev/null | grep -q ":$PORT "; then
    echo "Warning: Port $PORT appears to be in use"
    echo "You may need to use a different port with --port option"
fi

echo "Starting Mock DPSS Service..."
echo "API endpoint: http://$HOST:$PORT/api/v1/dpss/context"
echo "Health check: http://$HOST:$PORT/health"
echo "Data management: http://$HOST:$PORT/data"
echo ""
echo "Press Ctrl+C to stop the service"
echo ""

# Start the service
exec .venv/bin/python tools/mock_dpss_service.py "${ARGS[@]}" 