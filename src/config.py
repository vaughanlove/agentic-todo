"""Configuration management with environment variable support."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SignalConfig(BaseSettings):
    """Signal-CLI configuration."""

    cli_path: str = Field(default="/usr/local/bin/signal-cli")
    account: str = Field(default="")
    recipient: str = Field(default="")
    poll_interval: float = Field(default=5.0)

    model_config = SettingsConfigDict(
        env_prefix="SIGNAL_",
        env_file=".env",
        extra="ignore"
    )


class LinearConfig(BaseSettings):
    """Linear API configuration."""

    api_key: Optional[str] = Field(default=None)
    workspace_id: str = Field(default="")
    team_id: str = Field(default="")
    default_project_id: Optional[str] = Field(default=None)

    model_config = SettingsConfigDict(
        env_prefix="LINEAR_",
        env_file=".env",
        extra="ignore"
    )


class ClaudeConfig(BaseSettings):
    """Claude API configuration."""

    api_key: str = Field(default="")
    model: str = Field(default="claude-sonnet-4-5-20250929")
    max_tokens: int = Field(default=4096)
    temperature: float = Field(default=0.7)
    system_prompt: str = Field(
        default="You are a helpful task management assistant."
    )

    model_config = SettingsConfigDict(
        env_prefix="ANTHROPIC_",
        env_file=".env",
        extra="ignore"
    )


class QueueConfig(BaseSettings):
    """Queue management configuration."""

    max_workers: int = Field(default=3)
    max_size: int = Field(default=100)
    timeout: float = Field(default=30.0)

    model_config = SettingsConfigDict(
        env_prefix="QUEUE_",
        env_file=".env",
        extra="ignore"
    )


class RetryConfig(BaseSettings):
    """Retry configuration."""

    max_attempts: int = Field(default=3, alias="MAX_RETRIES")
    base_delay: float = Field(default=1.0, alias="RETRY_DELAY")
    max_delay: float = Field(default=60.0)
    exponential_backoff: bool = Field(default=True, alias="RETRY_BACKOFF")

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


class ErrorHandlingConfig(BaseSettings):
    """Error handling configuration."""

    notify_user: bool = Field(default=True)
    include_details: bool = Field(default=False)

    model_config = SettingsConfigDict(
        env_prefix="ERROR_",
        env_file=".env",
        extra="ignore"
    )


class LoggingConfig(BaseSettings):
    """Logging configuration."""

    level: str = Field(default="INFO", alias="LOG_LEVEL")
    format: str = Field(default="json")
    file: str = Field(default="logs/app.log", alias="LOG_FILE")
    max_bytes: int = Field(default=10485760)
    backup_count: int = Field(default=5)

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


class Config:
    """Main application configuration."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration from YAML file and environment variables.

        Args:
            config_path: Path to YAML configuration file
        """
        self.config_data: Dict[str, Any] = {}

        # Load YAML configuration if provided
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                self.config_data = yaml.safe_load(f) or {}

        # Initialize configuration sections
        self.signal = self._init_signal_config()
        self.linear = self._init_linear_config()
        self.claude = self._init_claude_config()
        self.queue = self._init_queue_config()
        self.retry = self._init_retry_config()
        self.error_handling = self._init_error_handling_config()
        self.logging = self._init_logging_config()

    def _init_signal_config(self) -> SignalConfig:
        """Initialize Signal configuration."""
        signal_data = self.config_data.get('signal', {})

        # Override with environment variables
        if phone := os.getenv('SIGNAL_PHONE_NUMBER'):
            signal_data['account'] = phone
        if recipient := os.getenv('SIGNAL_RECIPIENT'):
            signal_data['recipient'] = recipient

        return SignalConfig(**signal_data)

    def _init_linear_config(self) -> LinearConfig:
        """Initialize Linear configuration."""
        linear_data = self.config_data.get('linear', {})

        # Override with environment variable
        if api_key := os.getenv('LINEAR_API_KEY'):
            linear_data['api_key'] = api_key

        return LinearConfig(**linear_data)

    def _init_claude_config(self) -> ClaudeConfig:
        """Initialize Claude configuration."""
        claude_data = self.config_data.get('claude', {})

        # Override with environment variable
        if api_key := os.getenv('ANTHROPIC_API_KEY'):
            claude_data['api_key'] = api_key

        return ClaudeConfig(**claude_data)

    def _init_queue_config(self) -> QueueConfig:
        """Initialize queue configuration."""
        queue_data = self.config_data.get('queue', {})
        return QueueConfig(**queue_data)

    def _init_retry_config(self) -> RetryConfig:
        """Initialize retry configuration."""
        error_data = self.config_data.get('error_handling', {})
        retry_data = error_data.get('retry', {})
        return RetryConfig(**retry_data)

    def _init_error_handling_config(self) -> ErrorHandlingConfig:
        """Initialize error handling configuration."""
        error_data = self.config_data.get('error_handling', {})
        return ErrorHandlingConfig(**error_data)

    def _init_logging_config(self) -> LoggingConfig:
        """Initialize logging configuration."""
        logging_data = self.config_data.get('logging', {})
        return LoggingConfig(**logging_data)

    def validate(self) -> None:
        """
        Validate required configuration values.

        Raises:
            ValueError: If required configuration is missing
        """
        errors = []

        if not self.signal.account:
            errors.append("Signal account (phone number) is required")

        if not self.claude.api_key:
            errors.append("Anthropic API key is required")

        if not self.linear.workspace_id:
            errors.append("Linear workspace ID is required")

        if not self.linear.team_id:
            errors.append("Linear team ID is required")

        if errors:
            raise ValueError(
                "Configuration validation failed:\n" +
                "\n".join(f"  - {error}" for error in errors)
            )
