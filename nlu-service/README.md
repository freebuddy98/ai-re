# NLU Service

Natural Language Understanding Service for the AI-RE system. This service processes raw user messages and extracts structured information including user intent, entities, dialogue context, and action requirements.

## Features

- **Event-driven Architecture**: Integrates with the Event Bus Framework for reliable message processing
- **LLM Integration**: Uses Large Language Models for natural language understanding
- **DPSS Integration**: Connects with Dialogue Policy State Service for context management
- **Configurable**: Supports both YAML configuration files and environment variables
- **Scalable**: Supports consumer groups for horizontal scaling

## Architecture

The NLU service consists of several key components:

- **NLUProcessor**: Core processing logic that handles raw messages
- **PromptBuilder**: Constructs prompts for LLM interaction
- **Event Bus Integration**: Handles message subscription and publishing
- **Configuration Management**: Loads settings from YAML files and environment variables

## Installation

1. **Prerequisites**:
   - Python 3.8+
   - Poetry (for dependency management)
   - Redis (for event bus)

2. **Install Dependencies**:
   ```bash
   cd nlu-service
   poetry install
   ```

3. **Install Event Bus Framework**:
   ```bash
   # Activate virtual environment
   source .venv/bin/activate
   
   # Install event bus framework as local dependency
   pip install -e ../libs/event_bus_framework
   ```

## Configuration

The service can be configured using YAML files or environment variables.

### YAML Configuration

Create or update `config/config.yml` in the project root:

```yaml
nlu_service:
  service_name: "nlu-service"
  description: "Natural Language Understanding Service"
  version: "1.0.0"
  
  # DPSS Configuration
  dpss:
    base_url: "http://localhost:8080"
    timeout: 30.0
    context_limit: 5
  
  # LLM Configuration
  llm:
    model: "gpt-4-turbo"
    temperature: 0.2
    max_tokens: 2000
    timeout: 60.0
  
  # Event Topics
  topics:
    subscribe:
      - "user_message_raw"
    publish:
      - "nlu_uar_result"
  
  # Consumer Configuration
  consumer:
    group: "nlu-service-group"
    name: "nlu-worker-1"

# Event Bus Configuration
event_bus:
  stream_prefix: "ai-re"
  redis:
    host: "localhost"
    port: 6379
    db: 0
    password: ""
```

### Environment Variables

You can also configure the service using environment variables:

```bash
# Service Configuration
export NLU_SERVICE_NAME="nlu-service"
export NLU_LOG_LEVEL="INFO"

# LLM Configuration
export NLU_LLM_MODEL="gpt-4-turbo"
export NLU_LLM_TEMPERATURE="0.2"
export NLU_LLM_MAX_TOKENS="2000"
export NLU_LLM_TIMEOUT="60.0"

# DPSS Configuration
export NLU_DPSS_BASE_URL="http://localhost:8080"
export NLU_DPSS_TIMEOUT="30.0"
export NLU_DPSS_CONTEXT_LIMIT="5"

# Event Bus Configuration
export NLU_INPUT_TOPIC="user_message_raw"
export NLU_OUTPUT_TOPIC="nlu_uar_result"
export NLU_CONSUMER_GROUP="nlu-service-group"
export NLU_CONSUMER_NAME="nlu-worker-1"

# Redis Configuration
export REDIS_HOST="localhost"
export REDIS_PORT="6379"
export REDIS_DB="0"
export REDIS_PASSWORD=""
```

## Usage

### Running the Service

1. **Using the run script**:
   ```bash
   python run.py
   ```

2. **Using the module directly**:
   ```bash
   source .venv/bin/activate
   python -m nlu_service
   ```

3. **Using the main function**:
   ```bash
   source .venv/bin/activate
   python -c "from nlu_service import main; main()"
   ```

### Testing the Service

Run the test script to verify everything is working:

```bash
python test_service.py
```

### Using the NLU Processor Directly

You can also use the NLU processor directly in your code:

```python
from nlu_service import NLUProcessor
from nlu_service.config import get_config

# Load configuration
config = get_config()

# Create processor (you'll need to provide event_bus instance)
processor = NLUProcessor(
    event_bus=your_event_bus,
    input_topic="user_message_raw",
    output_topic="nlu_uar_result",
    consumer_group="nlu-service-group",
    llm_config=config.llm,
    dpss_config=config.dpss
)

# Process a message
message_data = {
    "user_id": "user123",
    "session_id": "session456",
    "raw_text": "I want to create a login system",
    "timestamp": "2024-01-01T12:00:00Z"
}

result = processor.process_raw_message(message_data)
print(result)
```

## Event Format

### Input Events (user_message_raw)

The service subscribes to `user_message_raw` events with the following format:

```json
{
  "user_id": "string",
  "session_id": "string", 
  "raw_text": "string",
  "timestamp": "ISO8601 timestamp",
  "metadata": {
    "channel": "web|mobile|api",
    "language": "en|zh|...",
    "context": {}
  }
}
```

### Output Events (nlu_uar_result)

The service publishes `nlu_uar_result` events with the following format:

```json
{
  "user_id": "string",
  "session_id": "string",
  "original_text": "string",
  "timestamp": "ISO8601 timestamp",
  "uar": {
    "user_intent": "string",
    "action_required": "string", 
    "entities": [
      {
        "type": "string",
        "value": "string",
        "confidence": 0.95
      }
    ],
    "requirements": [
      {
        "type": "functional|non_functional|constraint",
        "description": "string",
        "priority": "high|medium|low",
        "category": "string"
      }
    ]
  },
  "confidence": 0.95,
  "processing_time_ms": 150
}
```

## Development

### Project Structure

```
nlu-service/
├── src/nlu_service/
│   ├── __init__.py          # Package exports
│   ├── main.py              # Service entry point
│   ├── config.py            # Configuration management
│   ├── core/
│   │   ├── nlu_processor.py # Core NLU processing logic
│   │   └── prompt_builder.py # LLM prompt construction
│   └── models/              # Data models (if any)
├── tests/                   # Unit tests
├── run.py                   # Service runner script
├── test_service.py          # Service test script
├── pyproject.toml           # Dependencies and metadata
└── README.md                # This file
```

### Running Tests

```bash
# Activate virtual environment
source .venv/bin/activate

# Run unit tests
pytest tests/

# Run service integration test
python test_service.py
```

### Adding Dependencies

```bash
# Add runtime dependency
poetry add package_name

# Add development dependency  
poetry add --group dev package_name
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure all dependencies are installed and the virtual environment is activated
2. **Configuration Not Found**: Ensure `config/config.yml` exists in the project root or set environment variables
3. **Redis Connection Failed**: Check that Redis is running and accessible
4. **Event Bus Framework Not Found**: Install it as a local dependency: `pip install -e ../libs/event_bus_framework`

### Logging

The service uses structured logging. Set the log level using:

```bash
export NLU_LOG_LEVEL="DEBUG"  # DEBUG, INFO, WARNING, ERROR
```

Logs are output to stdout in JSON format by default.

## Contributing

1. Follow the existing code structure and patterns
2. Add unit tests for new functionality
3. Update this README if you add new features
4. Ensure all tests pass before submitting changes

## License

This project is part of the AI-RE system. See the main project license for details.
