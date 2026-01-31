# Contributing to Agentic Todo

Thank you for your interest in contributing to Agentic Todo!

## Development Setup

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/yourusername/agentic-todo.git
   cd agentic-todo
   ```

3. Set up development environment:
   ```bash
   make setup
   source venv/bin/activate
   ```

4. Create a branch for your feature:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Code Standards

### Python Style

- Follow PEP 8
- Use Black for formatting: `make format`
- Use type hints throughout
- Add docstrings to all public functions/classes

### Code Quality

Before submitting a PR:

```bash
# Format code
make format

# Run linters
make lint

# Run tests
make test

# Check coverage
make test-cov
```

All tests must pass and coverage should be maintained.

### Commit Messages

Use conventional commits:

- `feat: Add new feature`
- `fix: Fix bug in queue manager`
- `docs: Update README`
- `test: Add tests for error handler`
- `refactor: Improve retry logic`

## Testing

### Writing Tests

- Place tests in `tests/` directory
- Name test files `test_*.py`
- Use descriptive test names
- Include docstrings explaining what is tested

Example:
```python
@pytest.mark.asyncio
async def test_enqueue_message(queue_manager):
    """Test that messages are correctly enqueued."""
    message_id = await queue_manager.enqueue(
        sender="+1234567890",
        text="Test message"
    )
    assert message_id is not None
```

### Running Tests

```bash
# All tests
pytest

# Specific file
pytest tests/test_queue_manager.py

# With coverage
pytest --cov=src --cov-report=html

# Verbose output
pytest -v -s
```

## Documentation

- Update README.md for user-facing changes
- Add docstrings for all new functions/classes
- Update configuration examples if needed
- Include type hints

## Pull Request Process

1. Update the README.md with details of changes if needed
2. Update the version number following [SemVer](https://semver.org/)
3. Ensure all tests pass
4. Ensure code is formatted and linted
5. Request review from maintainers

### PR Checklist

- [ ] Code follows project style guidelines
- [ ] All tests pass
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] Commit messages are clear and descriptive
- [ ] No secrets or credentials in code

## Areas for Contribution

### High Priority

- [ ] Implement actual Linear API/MCP integration
- [ ] Add conversation persistence (database)
- [ ] Improve error recovery strategies
- [ ] Add metrics and monitoring

### Medium Priority

- [ ] Support for multiple users
- [ ] Add more task actions (archive, delete, etc.)
- [ ] Implement task reminders
- [ ] Add support for attachments

### Documentation

- [ ] API documentation
- [ ] Architecture diagrams
- [ ] Video tutorials
- [ ] Example use cases

## Code Review Guidelines

Reviewers should check:

- Code quality and readability
- Test coverage
- Error handling
- Documentation
- Performance implications
- Security considerations

## Getting Help

- Open an issue for bugs
- Start a discussion for features
- Ask questions in issues

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
