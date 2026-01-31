"""Retry utilities with exponential backoff for handling transient failures."""

import asyncio
import functools
from typing import Any, Callable, Optional, Tuple, Type, TypeVar, Union

from ..utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class RetryError(Exception):
    """Raised when all retry attempts have been exhausted."""

    def __init__(self, message: str, original_error: Exception, attempts: int):
        super().__init__(message)
        self.original_error = original_error
        self.attempts = attempts


def is_transient_error(error: Exception) -> bool:
    """
    Determine if an error is transient and worth retrying.

    Args:
        error: The exception to check

    Returns:
        True if the error is transient, False otherwise
    """
    # Network-related errors
    transient_types = (
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError,
    )

    if isinstance(error, transient_types):
        return True

    # Check error message for transient indicators
    error_msg = str(error).lower()
    transient_keywords = [
        'timeout',
        'connection',
        'temporary',
        'unavailable',
        'rate limit',
        'too many requests',
        '429',
        '502',
        '503',
        '504',
    ]

    return any(keyword in error_msg for keyword in transient_keywords)


async def retry_async(
    func: Callable[..., T],
    *args: Any,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_backoff: bool = True,
    retry_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    **kwargs: Any
) -> T:
    """
    Retry an async function with exponential backoff.

    Args:
        func: Async function to retry
        *args: Positional arguments for func
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_backoff: Use exponential backoff strategy
        retry_exceptions: Tuple of exception types to retry (None = retry all)
        **kwargs: Keyword arguments for func

    Returns:
        Result of the function call

    Raises:
        RetryError: When all retry attempts are exhausted
    """
    last_error: Optional[Exception] = None

    for attempt in range(1, max_attempts + 1):
        try:
            logger.debug(
                "Attempting function call",
                function=func.__name__,
                attempt=attempt,
                max_attempts=max_attempts
            )
            result = await func(*args, **kwargs)

            if attempt > 1:
                logger.info(
                    "Function succeeded after retry",
                    function=func.__name__,
                    attempt=attempt
                )

            return result

        except Exception as e:
            last_error = e

            # Check if we should retry this exception
            should_retry = (
                retry_exceptions is None or
                isinstance(e, retry_exceptions) or
                is_transient_error(e)
            )

            if not should_retry or attempt == max_attempts:
                logger.error(
                    "Function failed permanently",
                    function=func.__name__,
                    attempt=attempt,
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise RetryError(
                    f"Failed after {attempt} attempts: {str(e)}",
                    original_error=e,
                    attempts=attempt
                )

            # Calculate delay
            if exponential_backoff:
                delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            else:
                delay = base_delay

            logger.warning(
                "Function failed, retrying",
                function=func.__name__,
                attempt=attempt,
                max_attempts=max_attempts,
                error=str(e),
                error_type=type(e).__name__,
                retry_delay=delay
            )

            await asyncio.sleep(delay)

    # This should never be reached, but just in case
    if last_error:
        raise RetryError(
            f"Failed after {max_attempts} attempts",
            original_error=last_error,
            attempts=max_attempts
        )
    raise RuntimeError("Unexpected retry logic failure")


def retry_decorator(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_backoff: bool = True,
    retry_exceptions: Optional[Tuple[Type[Exception], ...]] = None
):
    """
    Decorator for retrying async functions with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_backoff: Use exponential backoff strategy
        retry_exceptions: Tuple of exception types to retry (None = retry all)

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await retry_async(
                func,
                *args,
                max_attempts=max_attempts,
                base_delay=base_delay,
                max_delay=max_delay,
                exponential_backoff=exponential_backoff,
                retry_exceptions=retry_exceptions,
                **kwargs
            )
        return wrapper
    return decorator
