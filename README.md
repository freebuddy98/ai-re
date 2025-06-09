# AI-RE Project

AI-powered Reactive Event processing system with Mattermost integration.

## Architecture Overview

The AI-RE system is built with a microservices architecture using event-driven patterns:

- **Input Service**: Handles webhook requests from Mattermost and publishes messages to event bus
- **Event Bus Framework**: Redis-based event streaming with message persistence
- **Configuration Management**: Centralized YAML-based configuration
- **Logging Integration**: Optional Loki logging for distributed log aggregation

## Quick Start

### Development Setup

1. **Clone and Setup Environment**
```bash
git clone <repository>
cd ai-re
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e libs/event_bus_framework
pip install -e services/input-service
pip install -r tests/requirements.txt
```

2. **Configure Services**
```bash
# Copy and edit configuration
cp config/config.yml.example config/config.yml
# Edit config/config.yml to match your environment
```

3. **Start Dependencies**
```bash
# Start Redis (required)
docker run -d --name redis -p 6379:6379 redis:alpine

# Start Loki (optional, for logging)
docker run -d --name loki -p 3100:3100 grafana/loki
```

### Container Deployment

#### Quick Start with Docker Compose
```bash
# Build and start all services
docker compose up -d

# Check service health
curl http://localhost:8000/health

# View logs
docker compose logs -f
```

#### Production Deployment
```bash
# Build production images
docker compose build --no-cache

# Start with production configuration
docker compose -f docker-compose.yml up -d

# Monitor services
docker compose ps
docker compose logs -f input-service
```

## Testing Framework

The AI-RE project includes a comprehensive testing framework with multiple test levels:

### Test Types

#### 1. Unit Tests
Fast, isolated tests for individual components:
```bash
./scripts/run_tests.sh --unit
```

#### 2. Integration Tests  
Tests for component interactions and external dependencies:
```bash
./scripts/run_tests.sh --integration
```

#### 3. End-to-End Tests
Complete workflow tests using TestClient:
```bash
./scripts/run_tests.sh --e2e
```

#### 4. **Container-Based Acceptance Tests** 🆕
Full system tests in Docker container environment:
```bash
./scripts/run_tests.sh --acceptance
```

### Container-Based Acceptance Testing

Our acceptance testing framework validates the complete system in a containerized environment, ensuring production-like reliability.

#### Test Coverage

**A001: Container Orchestration Startup Test**
- Validates Docker Compose service startup sequence
- Verifies container health checks and dependencies
- Tests service discovery and network communication

**A002: Inter-Service Network Communication Test** 
- Tests container-to-container network connectivity
- Validates DNS resolution within Docker network
- Measures network latency and reliability

**A003: API Endpoint Container Access Test**
- Validates external access through port mapping
- Tests all API endpoints in containerized environment
- Verifies response times and error handling

**A004: Data Persistence Verification Test**
- Tests Redis data persistence across container restarts
- Validates volume mounting and data integrity
- Verifies configuration file persistence

**A005: Environment Variable Configuration Test**
- Validates environment variable injection
- Tests configuration file loading in containers
- Verifies service-specific settings

**A006: Container Health Check and Auto-Recovery Test**
- Tests container health check mechanisms
- Validates automatic restart on failures
- Tests dependency startup ordering

**A007: Load Handling Container Performance Test**
- Concurrent request processing (100 requests, 20 workers)
- Resource usage monitoring (CPU, memory)
- Performance metrics validation (response times, throughput)

**A008: Log Collection and Management Test**
- Validates Loki log collection integration
- Tests log format and content correctness
- Verifies log query performance

**A009: Container Network Isolation Test**
- Tests network security and isolation
- Validates port access restrictions
- Ensures proper firewall configuration

**A010: Container Complete Lifecycle Test**
- Full container lifecycle management
- Graceful shutdown and startup testing
- Service availability verification

#### Running Acceptance Tests

**Quick Run - All Tests:**
```bash
./scripts/run_tests.sh --acceptance
```

**Individual Test Categories:**
```bash
# Container orchestration tests only
./scripts/run_container_acceptance_tests.sh --orchestration

# Performance tests only  
./scripts/run_container_acceptance_tests.sh --performance

# Data persistence tests only
./scripts/run_container_acceptance_tests.sh --persistence

# All acceptance tests with verbose output
./scripts/run_container_acceptance_tests.sh --all --verbose
```

**Environment Variables:**
```bash
# Skip acceptance tests
export SKIP_ACCEPTANCE_TESTS=true

# Enable verbose output
export VERBOSE=true
```

#### Prerequisites for Acceptance Tests

1. **Docker Environment:**
   - Docker 20.10+
   - Docker Compose v2.0+
   - Available ports: 8000, 6379, 3100

2. **Python Dependencies:**
   ```bash
   pip install docker pytest requests redis psutil
   ```

3. **System Resources:**
   - 2GB+ available RAM
   - 10GB+ available disk space
   - Network access for image pulling

#### Acceptance Test Reports

Tests generate comprehensive reports in `test-reports/acceptance/`:

- `container_status.txt` - Container state information
- `container_logs.txt` - Service logs during testing  
- `system_resources.txt` - Resource usage metrics

#### Performance Benchmarks

**Expected Performance Criteria:**
- **Success Rate:** > 95% for concurrent requests
- **Response Time:** < 500ms average, < 2s P99
- **Resource Usage:** < 512MB memory, < 80% CPU
- **Startup Time:** < 30s containers, < 60s service ready
- **Network Latency:** < 10ms between containers

### Complete Test Suite

Run all test levels:
```bash
# Run everything
./scripts/run_tests.sh --all

# Run with coverage report
./scripts/run_tests.sh --all --coverage

# Skip slow tests  
./scripts/run_tests.sh --all -m "not slow"
```

### Test Configuration

Control test execution with environment variables:
```bash
export SKIP_INTEGRATION_TESTS=true    # Skip integration tests
export SKIP_E2E_TESTS=true            # Skip end-to-end tests  
export SKIP_ACCEPTANCE_TESTS=true     # Skip acceptance tests
export REDIS_URL="redis://localhost:6379/0"
export LOKI_URL="http://localhost:3100/loki/api/v1/push"
```

## API Documentation

### Health Endpoints

**GET /health**
```json
{
  "status": "ok",
  "timestamp": "2025-06-09T15:18:32.390Z",
  "redis": {
    "status": "connected",
    "host": "redis:6379"
  }
}
```

**GET /loki-status**
```json
{
  "loki_enabled": true,
  "loki_url": "http://loki:3100/loki/api/v1/push"
}
```

### Webhook Endpoints

**POST /api/v1/webhook/mattermost**

Processes Mattermost outgoing webhook requests and publishes events to the message bus.

**Request Body:**
```json
{
  "token": "webhook-token",
  "team_id": "team123",
  "team_domain": "myteam",
  "channel_id": "channel456", 
  "channel_name": "general",
  "timestamp": 1622548800000,
  "user_id": "user789",
  "user_name": "johndoe",
  "post_id": "post123",
  "text": "Hello AI assistant!",
  "trigger_word": ""
}
```

**Response:**
```json
{
  "status": "ok",
  "message": "Webhook processed successfully"
}
```

## Configuration

### Configuration File Structure

The system uses a single `config/config.yml` file:

```yaml
event_bus:
  redis:
    url: "redis://redis:6379/0"
    max_connections: 10
    retry_on_timeout: true
    health_check_interval: 30
  topics:
    user_message_raw: "ai-re:user_message_raw"
  
logging:
  level: "INFO"
  enable_loki: true
  loki_url: "http://loki:3100/loki/api/v1/push"
```

### Environment Variables

Container deployment supports these environment variables:

- `REDIS_HOST` - Redis hostname (default: redis)
- `CONFIG_PATH` - Configuration file path
- `LOKI_URL` - Loki logging endpoint  
- `LOKI_ENABLED` - Enable/disable Loki logging
- `SERVICE_NAME` - Service identifier for logging

## Development

### Code Quality

```bash
# Format code
black services/ libs/

# Lint code  
flake8 services/ libs/

# Type checking
mypy services/input-service/src/
```

### Adding New Services

1. Create service directory in `services/`
2. Add `pyproject.toml` with dependencies
3. Implement service using event bus framework
4. Add Docker configuration
5. Update `docker-compose.yml`
6. Write tests (unit, integration, e2e, acceptance)

### Event Bus Integration

```python
from event_bus_framework import RedisStreamEventBus, get_logger

# Initialize event bus
event_bus = RedisStreamEventBus()

# Publish events
message_id = event_bus.publish(
    topic="user_message_raw",
    event_data={"user_id": "123", "text": "Hello"}
)

# Subscribe to events  
def message_handler(event_data):
    logger.info(f"Received: {event_data}")

event_bus.subscribe("user_message_raw", message_handler)
```

## Monitoring and Logs

### Container Monitoring

```bash
# View container status
docker compose ps

# Monitor resource usage
docker stats

# View service logs
docker compose logs -f input-service
docker compose logs -f redis
docker compose logs -f loki
```

### Log Aggregation

When Loki is enabled, all application logs are automatically shipped to Loki for centralized log management.

**Log Query Examples:**
```bash
# Query logs by service
curl -G -s "http://localhost:3100/loki/api/v1/query" \
  --data-urlencode 'query={service="input-service"}'

# Query error logs
curl -G -s "http://localhost:3100/loki/api/v1/query" \
  --data-urlencode 'query={level="ERROR"}'
```

## Troubleshooting

### Common Issues

**Container startup failures:**
```bash
# Check Docker daemon
docker info

# Check port conflicts
netstat -tulpn | grep :8000

# Rebuild images
docker compose build --no-cache
```

**Test failures:**
```bash
# Run with verbose output
./scripts/run_tests.sh --all --verbose

# Check specific test category
./scripts/run_tests.sh --integration --verbose

# Skip problematic test categories  
export SKIP_ACCEPTANCE_TESTS=true
./scripts/run_tests.sh --all
```

**Redis connection issues:**
```bash
# Test Redis connectivity
docker compose exec input-service python -c "import redis; r=redis.Redis(host='redis'); print(r.ping())"

# Check Redis logs
docker compose logs redis
```

**Performance issues:**
```bash
# Monitor resource usage
docker stats

# Check service logs
docker compose logs -f input-service

# Run performance tests
./scripts/run_container_acceptance_tests.sh --performance --verbose
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all test levels pass:
   ```bash
   ./scripts/run_tests.sh --all
   ```
5. Run acceptance tests to verify container compatibility:
   ```bash
   ./scripts/run_tests.sh --acceptance
   ```
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
