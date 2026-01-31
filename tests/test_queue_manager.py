"""Unit tests for QueueManager."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.queue_manager import MessageStatus, QueueManager, QueuedMessage


class TestQueuedMessage:
    """Test QueuedMessage dataclass."""

    def test_message_creation(self):
        """Test creating a queued message."""
        message = QueuedMessage(
            id="test-123",
            sender="+1234567890",
            text="Hello world",
            timestamp=datetime.now()
        )

        assert message.id == "test-123"
        assert message.sender == "+1234567890"
        assert message.text == "Hello world"
        assert message.status == MessageStatus.PENDING
        assert message.retry_count == 0

    def test_message_to_dict(self):
        """Test converting message to dictionary."""
        timestamp = datetime.now()
        message = QueuedMessage(
            id="test-123",
            sender="+1234567890",
            text="Hello world",
            timestamp=timestamp
        )

        data = message.to_dict()

        assert data["id"] == "test-123"
        assert data["sender"] == "+1234567890"
        assert data["text"] == "Hello world"
        assert data["status"] == "pending"
        assert isinstance(data["timestamp"], str)


class TestQueueManager:
    """Test QueueManager functionality."""

    @pytest.fixture
    def queue_manager(self):
        """Create a queue manager instance."""
        return QueueManager(
            max_workers=2,
            max_size=10,
            timeout=5.0
        )

    @pytest.mark.asyncio
    async def test_enqueue_message(self, queue_manager):
        """Test enqueueing a message."""
        message_id = await queue_manager.enqueue(
            sender="+1234567890",
            text="Test message"
        )

        assert message_id is not None
        assert message_id in queue_manager.messages
        assert queue_manager.queue.qsize() == 1

        message = queue_manager.get_message(message_id)
        assert message.sender == "+1234567890"
        assert message.text == "Test message"
        assert message.status == MessageStatus.PENDING

    @pytest.mark.asyncio
    async def test_enqueue_with_metadata(self, queue_manager):
        """Test enqueueing a message with metadata."""
        metadata = {"group_id": "abc123", "priority": "high"}

        message_id = await queue_manager.enqueue(
            sender="+1234567890",
            text="Test message",
            metadata=metadata
        )

        message = queue_manager.get_message(message_id)
        assert message.metadata == metadata

    @pytest.mark.asyncio
    async def test_queue_full(self):
        """Test behavior when queue is full."""
        queue_manager = QueueManager(max_size=2)

        # Fill queue
        await queue_manager.enqueue("+1111111111", "Message 1")
        await queue_manager.enqueue("+2222222222", "Message 2")

        # Try to enqueue one more
        with pytest.raises(asyncio.QueueFull):
            await queue_manager.enqueue("+3333333333", "Message 3")

    @pytest.mark.asyncio
    async def test_process_message_success(self, queue_manager):
        """Test successful message processing."""
        # Create a mock handler
        async def mock_handler(message):
            return f"Processed: {message.text}"

        message = QueuedMessage(
            id="test-123",
            sender="+1234567890",
            text="Test message",
            timestamp=datetime.now()
        )

        await queue_manager.process_message(message, mock_handler)

        assert message.status == MessageStatus.COMPLETED
        assert message.result == "Processed: Test message"
        assert message.started_at is not None
        assert message.completed_at is not None
        assert message.error is None

    @pytest.mark.asyncio
    async def test_process_message_timeout(self, queue_manager):
        """Test message processing timeout."""
        # Create a handler that takes too long
        async def slow_handler(message):
            await asyncio.sleep(10)
            return "Done"

        message = QueuedMessage(
            id="test-123",
            sender="+1234567890",
            text="Test message",
            timestamp=datetime.now()
        )

        await queue_manager.process_message(message, slow_handler)

        assert message.status == MessageStatus.TIMEOUT
        assert "timeout" in message.error.lower()
        assert message.result is None

    @pytest.mark.asyncio
    async def test_process_message_error(self, queue_manager):
        """Test message processing with error."""
        # Create a handler that raises an error
        async def error_handler(message):
            raise ValueError("Processing failed")

        message = QueuedMessage(
            id="test-123",
            sender="+1234567890",
            text="Test message",
            timestamp=datetime.now()
        )

        await queue_manager.process_message(message, error_handler)

        assert message.status == MessageStatus.FAILED
        assert "Processing failed" in message.error
        assert message.result is None

    @pytest.mark.asyncio
    async def test_worker_lifecycle(self, queue_manager):
        """Test worker start and stop."""
        processed_messages = []

        async def test_handler(message):
            processed_messages.append(message.id)
            return "Done"

        # Start workers
        await queue_manager.start(test_handler)
        assert queue_manager.running is True
        assert len(queue_manager.workers) == 2

        # Enqueue some messages
        msg1_id = await queue_manager.enqueue("+1111111111", "Message 1")
        msg2_id = await queue_manager.enqueue("+2222222222", "Message 2")

        # Give workers time to process
        await asyncio.sleep(0.5)

        # Stop workers
        await queue_manager.stop(wait=True)
        assert queue_manager.running is False
        assert len(queue_manager.workers) == 0

        # Check messages were processed
        assert msg1_id in processed_messages
        assert msg2_id in processed_messages

    @pytest.mark.asyncio
    async def test_stats(self, queue_manager):
        """Test statistics tracking."""
        async def test_handler(message):
            return "Done"

        await queue_manager.start(test_handler)

        # Enqueue and process messages
        await queue_manager.enqueue("+1111111111", "Message 1")
        await queue_manager.enqueue("+2222222222", "Message 2")

        # Wait for processing
        await queue_manager.queue.join()

        stats = queue_manager.get_stats()

        assert stats["total_processed"] == 2
        assert stats["successful"] == 2
        assert stats["failed"] == 0
        assert stats["timeout"] == 0
        assert stats["total_messages"] == 2

        await queue_manager.stop()

    @pytest.mark.asyncio
    async def test_get_message(self, queue_manager):
        """Test retrieving a message by ID."""
        message_id = await queue_manager.enqueue(
            sender="+1234567890",
            text="Test message"
        )

        message = queue_manager.get_message(message_id)
        assert message is not None
        assert message.id == message_id

        # Test non-existent message
        non_existent = queue_manager.get_message("non-existent-id")
        assert non_existent is None

    @pytest.mark.asyncio
    async def test_concurrent_processing(self, queue_manager):
        """Test concurrent message processing."""
        processing_times = []

        async def test_handler(message):
            start = asyncio.get_event_loop().time()
            await asyncio.sleep(0.1)  # Simulate work
            end = asyncio.get_event_loop().time()
            processing_times.append(end - start)
            return "Done"

        await queue_manager.start(test_handler)

        # Enqueue 4 messages
        for i in range(4):
            await queue_manager.enqueue(f"+{i}", f"Message {i}")

        # Wait for all to be processed
        await queue_manager.queue.join()

        # With 2 workers, 4 messages should be processed in ~0.2s total
        # (not 0.4s which would be sequential)
        assert len(processing_times) == 4

        await queue_manager.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
