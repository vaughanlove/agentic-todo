# Quick Start Guide

Get up and running with Agentic Todo in 5 minutes.

## Prerequisites

- Python 3.9+
- signal-cli installed
- Anthropic API key

## 1. Install signal-cli

**macOS:**
```bash
brew install signal-cli
```

**Linux:**
```bash
wget https://github.com/AsamK/signal-cli/releases/latest/download/signal-cli-*-Linux.tar.gz
tar xf signal-cli-*-Linux.tar.gz -C /opt
ln -sf /opt/signal-cli-*/bin/signal-cli /usr/local/bin/
```

## 2. Register Signal

```bash
# Replace with your phone number
export PHONE="+1234567890"

# Register
signal-cli -a $PHONE register

# Verify (you'll receive an SMS code)
signal-cli -a $PHONE verify 123456
```

## 3. Setup Project

```bash
# Clone and enter directory
cd agentic-todo

# Run setup
make setup

# Activate virtual environment
source venv/bin/activate
```

## 4. Configure

Edit `.env`:
```bash
SIGNAL_PHONE_NUMBER=+1234567890
SIGNAL_RECIPIENT=+0987654321
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

Edit `config.yaml`:
```yaml
linear:
  workspace_id: "your-workspace-id"  # Get from Linear settings
  team_id: "your-team-id"            # Get from Linear team URL

signal:
  account: "+1234567890"
  recipient: "+0987654321"
```

### Getting Linear IDs

1. Go to Linear settings → API
2. Your workspace ID is in the URL: `https://linear.app/WORKSPACE_ID/settings`
3. Team ID is in your team URL: `https://linear.app/TEAM_ID/team/TEAM_KEY`

## 5. Verify Setup

```bash
python scripts/verify_setup.py
```

If all checks pass, you're ready!

## 6. Run

```bash
make run
```

Or directly:
```bash
python -m src.main
```

## 7. Send Your First Task

From your phone, send a Signal message to the configured number:

```
Create a task to review the documentation
```

You should receive a response from Claude confirming the task creation!

## Common Issues

### "signal-cli not found"
```bash
which signal-cli
# If not found, reinstall signal-cli
```

### "Not registered"
```bash
signal-cli -a +YOUR_NUMBER register
signal-cli -a +YOUR_NUMBER verify CODE
```

### "Invalid API key"
- Double-check your `.env` file
- Get a new key from https://console.anthropic.com

### No messages received
```bash
# Test signal-cli directly
signal-cli -a +YOUR_NUMBER receive
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [CONTRIBUTING.md](CONTRIBUTING.md) to contribute
- Run tests: `make test`
- View logs: `tail -f logs/app.log`

## Example Usage

**Create tasks:**
```
Create a high priority task to fix the login bug
Add a task to review PR #123
New task: Update documentation
```

**List tasks:**
```
Show me my tasks
What are my urgent tasks?
List all open issues
```

**Update tasks:**
```
Mark ENG-456 as complete
Update task ENG-123 to high priority
```

## Getting Help

- Check logs: `tail -f logs/app.log`
- Run verification: `python scripts/verify_setup.py`
- Open an issue on GitHub
