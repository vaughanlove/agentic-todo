"""Centralized error handling with user-friendly messaging."""

import traceback
from enum import Enum
from typing import Any, Optional

from .utils.logger import get_logger

logger = get_logger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""

    SIGNAL = "signal"
    LINEAR = "linear"
    CLAUDE = "claude"
    QUEUE = "queue"
    CONFIGURATION = "configuration"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


class AppError(Exception):
    """Base application error with context."""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        user_message: Optional[str] = None,
        original_error: Optional[Exception] = None,
        context: Optional[dict] = None
    ):
        """
        Initialize application error.

        Args:
            message: Technical error message
            category: Error category
            severity: Error severity
            user_message: User-friendly error message
            original_error: Original exception if wrapped
            context: Additional context dictionary
        """
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.user_message = user_message or self._generate_user_message()
        self.original_error = original_error
        self.context = context or {}

    def _generate_user_message(self) -> str:
        """Generate a user-friendly error message."""
        category_messages = {
            ErrorCategory.SIGNAL: "Unable to send/receive Signal messages. Please check your Signal setup.",
            ErrorCategory.LINEAR: "Unable to access Linear tasks. Please verify your Linear configuration.",
            ErrorCategory.CLAUDE: "AI assistant is temporarily unavailable. Please try again.",
            ErrorCategory.QUEUE: "System is busy processing requests. Please try again shortly.",
            ErrorCategory.CONFIGURATION: "System configuration error. Please contact support.",
            ErrorCategory.VALIDATION: "Invalid request. Please check your message and try again.",
        }
        return category_messages.get(
            self.category,
            "An unexpected error occurred. Please try again."
        )


class SignalError(AppError):
    """Signal-related errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.SIGNAL,
            **kwargs
        )


class LinearError(AppError):
    """Linear-related errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.LINEAR,
            **kwargs
        )


class ClaudeError(AppError):
    """Claude API-related errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.CLAUDE,
            **kwargs
        )


class QueueError(AppError):
    """Queue management errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.QUEUE,
            **kwargs
        )


class ErrorHandler:
    """Centralized error handling and logging."""

    def __init__(self, notify_user: bool = True, include_details: bool = False):
        """
        Initialize error handler.

        Args:
            notify_user: Whether to send error notifications to users
            include_details: Include technical details in user notifications
        """
        self.notify_user = notify_user
        self.include_details = include_details
        self.logger = get_logger(__name__)

    async def handle_error(
        self,
        error: Exception,
        context: Optional[dict] = None,
        user_id: Optional[str] = None
    ) -> str:
        """
        Handle an error with logging and optional user notification.

        Args:
            error: The exception to handle
            context: Additional context information
            user_id: User ID for targeted notifications

        Returns:
            User-friendly error message
        """
        context = context or {}

        # Convert to AppError if needed
        if not isinstance(error, AppError):
            app_error = AppError(
                message=str(error),
                original_error=error,
                context=context
            )
        else:
            app_error = error
            app_error.context.update(context)

        # Log the error
        self._log_error(app_error, user_id)

        # Generate user message
        user_message = self._format_user_message(app_error)

        return user_message

    def _log_error(self, error: AppError, user_id: Optional[str] = None) -> None:
        """Log error with full context."""
        log_context = {
            "category": error.category.value,
            "severity": error.severity.value,
            "user_id": user_id,
            **error.context
        }

        if error.original_error:
            log_context["original_error"] = str(error.original_error)
            log_context["traceback"] = traceback.format_exc()

        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(error.message, **log_context)
        elif error.severity == ErrorSeverity.HIGH:
            self.logger.error(error.message, **log_context)
        elif error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(error.message, **log_context)
        else:
            self.logger.info(error.message, **log_context)

    def _format_user_message(self, error: AppError) -> str:
        """Format user-friendly error message."""
        if not self.notify_user:
            return ""

        message = f"⚠️ {error.user_message}"

        if self.include_details and error.message:
            message += f"\n\nDetails: {error.message}"

        return message

    def wrap_error(
        self,
        error: Exception,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[dict] = None
    ) -> AppError:
        """
        Wrap a generic exception in an AppError.

        Args:
            error: Original exception
            message: Technical error message
            category: Error category
            severity: Error severity
            context: Additional context

        Returns:
            Wrapped AppError
        """
        return AppError(
            message=message,
            category=category,
            severity=severity,
            original_error=error,
            context=context
        )
