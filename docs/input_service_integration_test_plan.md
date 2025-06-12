# Input-Service Integration Test Plan

## Overview
The purpose of this plan is to validate that the **input-service** works correctly as an entry point for external messages and integrates properly with dependent components such as Redis Streams event bus, Loki logging system, and configuration management.

The planned test cases are implemented with **pytest** and FastAPI's `TestClient` and live Redis and Loki services.

| ID | Title | Component(s) | Happy / Edge | Preconditions | Test Steps | Expected Results |
|----|-------|--------------|--------------|---------------|------------|------------------|
| INT-IS-001 | Webhook happy path | FastAPI endpoint `/api/v1/webhook/mattermost`, EventBus, Redis | Happy | 1. Redis is up and reachable<br>2. Valid JSON payload is prepared | 1. POST payload to endpoint.<br>2. Read message from Redis stream `ai-re:user_message_raw` | 1. HTTP 200 response<br>2. Message appears in Redis stream with correct structure |
| INT-IS-002 | Health endpoint | FastAPI endpoint `/health` | Happy | 1. Service is running | 1. GET `/health` | 1. HTTP 200 response<br>2. JSON with `{"status": "ok"}` |
| INT-IS-003 | Empty message handling | FastAPI endpoint `/api/v1/webhook/mattermost` | Edge | 1. Service is running | 1. POST with empty/null `text` field | 1. HTTP 200 response<br>2. Response indicates message was ignored |
| INT-IS-004 | Malformed data handling | FastAPI endpoint `/api/v1/webhook/mattermost` | Edge | 1. Service is running | 1. POST with invalid/missing required fields | 1. HTTP 200 response<br>2. Error is logged and handled gracefully |
| INT-IS-005 | Loki status endpoint | FastAPI endpoint `/loki-status` | Happy | 1. Service is running | 1. GET `/loki-status` | 1. HTTP 200 response<br>2. JSON with Loki configuration status |
| INT-IS-006 | Loki log integration | Loki logging system, logcli | Happy | 1. Loki service is running<br>2. logcli tool is available | 1. POST webhook to generate logs<br>2. Query Loki with logcli<br>3. Verify logs are present | 1. Webhook processes successfully<br>2. Logs appear in Loki<br>3. Logs contain service information |
| INT-IS-007 | Loki service availability | Loki service endpoints | Happy | 1. Loki service is deployed | 1. GET `/ready` endpoint<br>2. GET `/loki/api/v1/labels` endpoint | 1. Both endpoints return HTTP 200<br>2. Loki service is responsive |
| INT-IS-008 | Configuration integration | Config management system | Happy | 1. Config file exists or defaults are used | 1. Service reads config<br>2. Verify config values | 1. Service starts successfully<br>2. Config values are loaded correctly |
| INT-IS-009 | Event bus integration | Redis Streams, EventBus interface | Happy | 1. Redis is running<br>2. EventBus is initialized | 1. Create EventBus instance<br>2. Test publish/subscribe operations | 1. EventBus connects to Redis<br>2. Publish/subscribe operations work |

## Test Environment

### Docker Services
- **redis**: Redis Alpine image for message streaming
- **loki**: Grafana Loki latest image for log aggregation  
- **input-service**: Built from local Dockerfile
- **test-runner-input**: Test runner with pytest, logcli, and all dependencies

### Volume Mounts
Source code is mounted as read-only volumes to avoid rebuilding images:
- `input-service/src` → `/app/input-service/src`
- `libs` → `/app/libs` 
- `tests` → `/app/tests`
- `config` → `/app/config`

### Environment Variables
- `REDIS_HOST=redis`
- `REDIS_PORT=6379`
- `LOKI_URL=http://loki:3100`

## Running Tests

```bash
# Run with Chinese mirror for faster builds
make test-integration-input USE_CHINA_MIRROR=true

# Run with default mirrors
make test-integration-input
```

## Expected Outcomes
All test cases should pass, demonstrating that:
1. HTTP endpoints respond correctly
2. Message processing pipeline works end-to-end
3. Error handling is robust
4. Logging integration with Loki functions properly
5. Configuration and event bus integration work as expected

## Environment
• Test framework: `pytest` 8.x<br>• Dependencies: `redis` container/service available at host defined by env or default `redis:6379`.<br>• All tests are located under `tests/integration/` and can be executed via `pytest -m "not skip_integration"` or just `pytest` when Redis is reachable.

## Skip Strategy
If Redis is not available (detected by `redis_client.ping()` raising `ConnectionError`) the relevant tests are dynamically skipped so that the CI pipeline does not fail for environments without external services.

---
Author: AI-RE QA Team
Date: 2025-06-12 