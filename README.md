# Agentic Todo

AI-powered task management system that integrates Signal messaging, Linear issue tracking, and Claude AI for natural language task management.

## Features

- 📱 **Signal Integration**: Send and receive tasks via Signal messages
- 🎯 **Linear Integration**: Automatic task creation and management in Linear
- 🤖 **Claude AI**: Natural language processing for intelligent task handling
- 🔄 **Queue Management**: Concurrent message processing with retry logic
- 📊 **Robust Error Handling**: Comprehensive error handling with user-friendly notifications
- 📝 **Structured Logging**: JSON logging with full context tracking
- 🔁 **Automatic Retries**: Exponential backoff for transient failures

## Architecture

```
┌─────────────┐
│   Signal    │ ──► Messages via signal-cli
└─────────────┘
       │
       ▼
┌─────────────┐
│    Queue    │ ──► Concurrent processing
│   Manager   │
└─────────────┘
       │
       ▼
┌─────────────┐
│   Message   │ ──► Coordinates response
│   Handler   │
└─────────────┘
       │
       ├──► Claude AI (NLP processing)
       │
       └──► Linear (Task management)
```

## Prerequisites

- Python 3.9 or higher
- signal-cli installed and configured
- Linear account with API access or MCP server
- Anthropic API key

## Installation

### 1. Install signal-cli

**macOS:**
```bash
brew install signal-cli
```

**Linux:**
```bash
# Download latest release from https://github.com/AsamK/signal-cli/releases
wget https://github.com/AsamK/signal-cli/releases/download/v0.12.3/signal-cli-0.12.3-Linux.tar.gz
tar xf signal-cli-0.12.3-Linux.tar.gz -C /opt
ln -sf /opt/signal-cli-0.12.3/bin/signal-cli /usr/local/bin/
```

### 2. Register Signal Phone Number

```bash
# Register your phone number
signal-cli -a +YOUR_PHONE_NUMBER register

# Verify with the code you receive via SMS
signal-cli -a +YOUR_PHONE_NUMBER verify CODE
```

### 3. Install Linear MCP Server

Follow the instructions at: https://github.com/modelcontextprotocol/servers/tree/main/src/linear

Alternatively, use the Linear GraphQL API directly by setting `LINEAR_API_KEY` in your environment.

### 4. Clone and Setup Project

```bash
# Clone repository
git clone https://github.com/yourusername/agentic-todo.git
cd agentic-todo

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 5. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Required environment variables:
```bash
# Signal Configuration
SIGNAL_PHONE_NUMBER=+1234567890
SIGNAL_RECIPIENT=+0987654321

# Anthropic API
ANTHROPIC_API_KEY=sk-ant-xxxxx

# Linear (if not using MCP)
LINEAR_API_KEY=lin_api_xxxxx

# Optional
LOG_LEVEL=INFO
MAX_RETRIES=3
```

### 6. Configure Application

```bash
# Copy example config
cp config.yaml.example config.yaml

# Edit configuration
nano config.yaml
```

Update these critical fields:
```yaml
linear:
  workspace_id: "your-workspace-id"
  team_id: "your-team-id"

signal:
  account: "+1234567890"
  recipient: "+0987654321"
```

## Usage

### Start the Application

```bash
# Using the CLI
python -m src.main

# Or with custom config
python -m src.main --config /path/to/config.yaml

# Or use the entry point
python src/main.py
```

### Send Commands via Signal

Send messages to your configured Signal number:

**Create a task:**
```
Create a task to fix the login bug
```

**List tasks:**
```
Show me my current tasks
```

**Update a task:**
```
Mark task ENG-123 as complete
```

**Priority tasks:**
```
Create a high priority task to review PR #456
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_queue_manager.py -v
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type checking
mypy src/
```

### Project Structure

```
agentic-todo/
├── src/
│   ├── main.py              # Main entry point
│   ├── config.py            # Configuration management
│   ├── signal_client.py     # Signal-CLI integration
│   ├── linear_client.py     # Linear API integration
│   ├── claude_client.py     # Claude AI integration
│   ├── queue_manager.py     # Message queue management
│   ├── error_handler.py     # Error handling
│   ├── handlers/
│   │   └── message_handler.py  # Message processing
│   └── utils/
│       ├── logger.py        # Logging setup
│       └── retry.py         # Retry logic
├── tests/
│   ├── conftest.py          # Test configuration
│   └── test_queue_manager.py  # Queue manager tests
├── logs/                    # Log files
├── config.yaml              # Application configuration
├── .env                     # Environment variables
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Configuration

### Signal Configuration

```yaml
signal:
  cli_path: "/usr/local/bin/signal-cli"
  account: "+1234567890"
  recipient: "+0987654321"
  poll_interval: 5.0  # seconds
```

### Linear Configuration

```yaml
linear:
  workspace_id: "your-workspace-id"
  team_id: "your-team-id"
  default_project_id: "your-project-id"
```

### Queue Configuration

```yaml
queue:
  max_workers: 3        # Concurrent message processors
  max_size: 100         # Maximum queue size
  timeout: 30.0         # Message processing timeout
```

### Error Handling

```yaml
error_handling:
  notify_user: true           # Send error messages via Signal
  include_details: false      # Include technical details
  retry:
    max_attempts: 3
    base_delay: 1.0
    max_delay: 60.0
    exponential_backoff: true
```

## Error Handling

The system includes comprehensive error handling:

- **Signal Errors**: Connection issues, message send failures
- **Linear Errors**: API failures, authentication issues
- **Claude Errors**: Rate limits, API errors
- **Queue Errors**: Queue full, processing timeouts

All errors are:
1. Logged with full context
2. Categorized by severity
3. Optionally sent to users via Signal
4. Automatically retried if transient

## Logging

Logs are written to:
- Console (stdout) - for monitoring
- File (logs/app.log) - for persistence

Log format:
```json
{
  "timestamp": "2025-01-31T10:30:45.123Z",
  "level": "INFO",
  "logger": "src.queue_manager",
  "message": "Message processed successfully",
  "context": {
    "message_id": "abc-123",
    "processing_time": 2.5
  }
}
```

## Monitoring

### View Queue Statistics

The application logs queue statistics periodically:

```json
{
  "total_processed": 150,
  "successful": 145,
  "failed": 3,
  "timeout": 2,
  "avg_processing_time": 3.2,
  "queue_size": 5,
  "active_workers": 3
}
```

### Check Logs

```bash
# Tail logs
tail -f logs/app.log

# Search for errors
grep ERROR logs/app.log

# View JSON logs with jq
cat logs/app.log | jq 'select(.level == "ERROR")'
```

## Troubleshooting

### Signal-CLI Issues

**Problem**: "signal-cli not found"
```bash
# Verify installation
which signal-cli

# Test signal-cli
signal-cli -a +YOUR_NUMBER receive
```

**Problem**: "Not registered"
```bash
# Re-register
signal-cli -a +YOUR_NUMBER register
signal-cli -a +YOUR_NUMBER verify CODE
```

### Linear API Issues

**Problem**: "Authentication failed"
- Verify your Linear API key is correct
- Check workspace and team IDs in config.yaml

### Claude API Issues

**Problem**: "Rate limit exceeded"
- The system will automatically retry
- Consider reducing `queue.max_workers` in config

**Problem**: "Invalid API key"
- Verify `ANTHROPIC_API_KEY` is set correctly
- Get a new key from https://console.anthropic.com

## Security Considerations

- Never commit `.env` file to version control
- Store API keys securely (use environment variables)
- Restrict Signal account access
- Use HTTPS for all API calls
- Regularly rotate API keys

## Performance Tuning

### High Volume Usage

Adjust these settings in `config.yaml`:

```yaml
queue:
  max_workers: 5      # Increase concurrent processing
  max_size: 200       # Increase queue capacity

error_handling:
  retry:
    max_attempts: 5   # More retries for reliability
```

### Low Latency

```yaml
signal:
  poll_interval: 1.0  # More frequent polling

queue:
  timeout: 10.0       # Faster timeout
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run tests and linters
6. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- GitHub Issues: https://github.com/yourusername/agentic-todo/issues
- Documentation: https://github.com/yourusername/agentic-todo/wiki

## Acknowledgments

- [signal-cli](https://github.com/AsamK/signal-cli) for Signal integration
- [Anthropic](https://www.anthropic.com) for Claude AI
- [Linear](https://linear.app) for task management
