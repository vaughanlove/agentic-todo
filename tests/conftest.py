"""Pytest configuration and shared fixtures."""

import os
import sys
from pathlib import Path

import pytest

# Add src directory to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture(autouse=True)
def env_setup(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-api-key")
    monkeypatch.setenv("SIGNAL_PHONE_NUMBER", "+1234567890")
    monkeypatch.setenv("SIGNAL_RECIPIENT", "+0987654321")
    monkeypatch.setenv("LINEAR_API_KEY", "test-linear-key")
    monkeypatch.setenv("LOG_LEVEL", "ERROR")


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    from src.config import Config

    config = Config()
    config.signal.account = "+1234567890"
    config.claude.api_key = "test-api-key"
    config.linear.workspace_id = "test-workspace"
    config.linear.team_id = "test-team"

    return config
