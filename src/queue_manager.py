"""Message queue manager for handling concurrent task processing."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from .utils.logger import get_logger

logger = get_logger(__name__)


class MessageStatus(Enum):
    """Message processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class QueuedMessage:
    """Represents a queued message for processing."""

    id: str
    sender: str
    text: str
    timestamp: datetime
    status: MessageStatus = MessageStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[str] = None
    error: Optional[str] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "sender": self.sender,
            "text": self.text,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count,
            "metadata": self.metadata
        }


class QueueManager:
    """Manages message processing queue with concurrency control."""

    def __init__(
        self,
        max_workers: int = 3,
        max_size: int = 100,
        timeout: float = 30.0
    ):
        """
        Initialize queue manager.

        Args:
            max_workers: Maximum concurrent workers
            max_size: Maximum queue size
            timeout: Message processing timeout in seconds
        """
        self.max_workers = max_workers
        self.max_size = max_size
        self.timeout = timeout

        self.queue: asyncio.Queue[QueuedMessage] = asyncio.Queue(maxsize=max_size)
        self.messages: Dict[str, QueuedMessage] = {}
        self.workers: list[asyncio.Task] = []
        self.running = False

        self.logger = get_logger(__name__)

        # Statistics
        self.stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "timeout": 0,
            "avg_processing_time": 0.0
        }

    async def enqueue(
        self,
        sender: str,
        text: str,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a message to the processing queue.

        Args:
            sender: Message sender
            text: Message text
            timestamp: Message timestamp
            metadata: Additional metadata

        Returns:
            Message ID

        Raises:
            asyncio.QueueFull: If queue is full
        """
        message = QueuedMessage(
            id=str(uuid4()),
            sender=sender,
            text=text,
            timestamp=timestamp or datetime.now(),
            metadata=metadata or {}
        )

        try:
            self.queue.put_nowait(message)
            self.messages[message.id] = message

            self.logger.info(
                "Message enqueued",
                message_id=message.id,
                sender=sender,
                queue_size=self.queue.qsize()
            )

            return message.id

        except asyncio.QueueFull:
            self.logger.error(
                "Queue is full, cannot enqueue message",
                max_size=self.max_size,
                current_size=self.queue.qsize()
            )
            raise

    async def process_message(
        self,
        message: QueuedMessage,
        handler: Any
    ) -> None:
        """
        Process a single message.

        Args:
            message: Message to process
            handler: Message handler function
        """
        message.status = MessageStatus.PROCESSING
        message.started_at = datetime.now()

        self.logger.info(
            "Processing message",
            message_id=message.id,
            sender=message.sender
        )

        try:
            # Process with timeout
            result = await asyncio.wait_for(
                handler(message),
                timeout=self.timeout
            )

            message.status = MessageStatus.COMPLETED
            message.result = result
            message.completed_at = datetime.now()

            self.stats["successful"] += 1

            processing_time = (
                message.completed_at - message.started_at
            ).total_seconds()

            self.logger.info(
                "Message processed successfully",
                message_id=message.id,
                processing_time=processing_time
            )

        except asyncio.TimeoutError:
            message.status = MessageStatus.TIMEOUT
            message.error = f"Processing timeout after {self.timeout}s"
            message.completed_at = datetime.now()

            self.stats["timeout"] += 1

            self.logger.error(
                "Message processing timeout",
                message_id=message.id,
                timeout=self.timeout
            )

        except Exception as e:
            message.status = MessageStatus.FAILED
            message.error = str(e)
            message.completed_at = datetime.now()

            self.stats["failed"] += 1

            self.logger.error(
                "Message processing failed",
                message_id=message.id,
                error=str(e),
                error_type=type(e).__name__
            )

        finally:
            self.stats["total_processed"] += 1

            # Update average processing time
            if message.completed_at and message.started_at:
                processing_time = (
                    message.completed_at - message.started_at
                ).total_seconds()

                self.stats["avg_processing_time"] = (
                    (self.stats["avg_processing_time"] *
                     (self.stats["total_processed"] - 1) +
                     processing_time) /
                    self.stats["total_processed"]
                )

    async def worker(self, worker_id: int, handler: Any) -> None:
        """
        Worker coroutine for processing messages.

        Args:
            worker_id: Worker identifier
            handler: Message handler function
        """
        self.logger.info(f"Worker {worker_id} started")

        while self.running:
            try:
                # Get message from queue with timeout
                message = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=1.0
                )

                await self.process_message(message, handler)

                self.queue.task_done()

            except asyncio.TimeoutError:
                # No message available, continue
                continue
            except Exception as e:
                self.logger.error(
                    f"Worker {worker_id} error",
                    error=str(e),
                    error_type=type(e).__name__
                )

        self.logger.info(f"Worker {worker_id} stopped")

    async def start(self, handler: Any) -> None:
        """
        Start the queue processing workers.

        Args:
            handler: Message handler function
        """
        if self.running:
            self.logger.warning("Queue manager already running")
            return

        self.running = True
        self.logger.info(
            "Starting queue manager",
            max_workers=self.max_workers,
            max_size=self.max_size,
            timeout=self.timeout
        )

        # Create worker tasks
        for i in range(self.max_workers):
            task = asyncio.create_task(self.worker(i, handler))
            self.workers.append(task)

    async def stop(self, wait: bool = True) -> None:
        """
        Stop the queue processing workers.

        Args:
            wait: Wait for queue to be empty before stopping
        """
        if not self.running:
            return

        self.logger.info("Stopping queue manager", wait_for_empty=wait)

        if wait:
            # Wait for queue to be empty
            await self.queue.join()

        self.running = False

        # Cancel all workers
        for worker in self.workers:
            worker.cancel()

        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)

        self.workers.clear()

        self.logger.info("Queue manager stopped", stats=self.stats)

    def get_message(self, message_id: str) -> Optional[QueuedMessage]:
        """
        Get message by ID.

        Args:
            message_id: Message ID

        Returns:
            Message or None if not found
        """
        return self.messages.get(message_id)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics.

        Returns:
            Statistics dictionary
        """
        return {
            **self.stats,
            "queue_size": self.queue.qsize(),
            "active_workers": len(self.workers),
            "total_messages": len(self.messages)
        }
