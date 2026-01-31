"""Main entry point for the agentic todo system."""

import asyncio
import signal as signal_module
import sys
from pathlib import Path
from typing import Optional

from .claude_client import ClaudeClient
from .config import Config
from .error_handler import ErrorHandler
from .handlers.message_handler import MessageHandler
from .linear_client import LinearClient
from .queue_manager import QueueManager
from .signal_client import SignalClient, SignalMessage
from .utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


class AgenticTodoApp:
    """Main application for agentic todo management."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the application.

        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config = Config(config_path)

        # Setup logging
        setup_logging(
            log_level=self.config.logging.level,
            log_file=self.config.logging.file,
            json_format=(self.config.logging.format == "json")
        )

        self.logger = get_logger(__name__)
        self.logger.info("Initializing Agentic Todo application")

        # Validate configuration
        try:
            self.config.validate()
        except ValueError as e:
            self.logger.critical(f"Configuration validation failed: {e}")
            sys.exit(1)

        # Initialize clients
        retry_config = {
            "max_attempts": self.config.retry.max_attempts,
            "base_delay": self.config.retry.base_delay,
            "max_delay": self.config.retry.max_delay,
            "exponential_backoff": self.config.retry.exponential_backoff
        }

        self.signal_client = SignalClient(self.config.signal, retry_config)
        self.linear_client = LinearClient(self.config.linear, retry_config)
        self.claude_client = ClaudeClient(self.config.claude, retry_config)

        # Initialize error handler
        self.error_handler = ErrorHandler(
            notify_user=self.config.error_handling.notify_user,
            include_details=self.config.error_handling.include_details
        )

        # Initialize message handler
        self.message_handler = MessageHandler(
            signal_client=self.signal_client,
            linear_client=self.linear_client,
            claude_client=self.claude_client,
            error_handler=self.error_handler
        )

        # Initialize queue manager
        self.queue_manager = QueueManager(
            max_workers=self.config.queue.max_workers,
            max_size=self.config.queue.max_size,
            timeout=self.config.queue.timeout
        )

        # Shutdown flag
        self.shutdown_event = asyncio.Event()

    async def process_signal_messages(self) -> None:
        """Poll for and process incoming Signal messages."""
        self.logger.info("Starting Signal message polling")

        while not self.shutdown_event.is_set():
            try:
                # Receive messages from Signal
                messages = await self.signal_client.receive_messages(
                    timeout=self.config.signal.poll_interval
                )

                # Enqueue each message for processing
                for msg in messages:
                    try:
                        await self.queue_manager.enqueue(
                            sender=msg.sender,
                            text=msg.text,
                            timestamp=msg.timestamp,
                            metadata={
                                "group_id": msg.group_id,
                                "attachments": msg.attachments
                            }
                        )

                        self.logger.info(
                            "Message enqueued",
                            sender=msg.sender,
                            text_preview=msg.text[:50]
                        )

                    except asyncio.QueueFull:
                        self.logger.error(
                            "Queue full, cannot process message",
                            sender=msg.sender
                        )

                        # Send error notification to user
                        await self.signal_client.send_error_notification(
                            msg.sender,
                            "⚠️ System is currently busy. Please try again in a few moments."
                        )

                # Small delay between polls
                await asyncio.sleep(1.0)

            except Exception as e:
                self.logger.error(
                    "Error in message polling loop",
                    error=str(e),
                    error_type=type(e).__name__
                )

                # Wait before retrying
                await asyncio.sleep(5.0)

        self.logger.info("Signal message polling stopped")

    async def run(self) -> None:
        """Run the main application loop."""
        self.logger.info("Starting Agentic Todo application")

        try:
            # Start queue manager
            await self.queue_manager.start(self.message_handler.handle)

            # Start Signal message polling
            polling_task = asyncio.create_task(self.process_signal_messages())

            # Wait for shutdown signal
            await self.shutdown_event.wait()

            # Stop polling
            polling_task.cancel()
            try:
                await polling_task
            except asyncio.CancelledError:
                pass

            # Stop queue manager
            await self.queue_manager.stop(wait=True)

            # Log final statistics
            stats = self.queue_manager.get_stats()
            self.logger.info("Application stopped", stats=stats)

        except Exception as e:
            self.logger.critical(
                "Fatal error in main loop",
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    def handle_shutdown_signal(self, sig: int) -> None:
        """
        Handle shutdown signals gracefully.

        Args:
            sig: Signal number
        """
        signal_name = signal_module.Signals(sig).name
        self.logger.info(f"Received shutdown signal: {signal_name}")
        self.shutdown_event.set()

    async def start(self) -> None:
        """Start the application with signal handlers."""
        # Register signal handlers
        loop = asyncio.get_event_loop()

        for sig in (signal_module.SIGTERM, signal_module.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda s=sig: self.handle_shutdown_signal(s)
            )

        # Run application
        await self.run()


async def main(config_path: Optional[str] = None) -> None:
    """
    Main entry point.

    Args:
        config_path: Path to configuration file
    """
    app = AgenticTodoApp(config_path)
    await app.start()


def cli() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Agentic Todo - AI-powered task management via Signal"
    )
    parser.add_argument(
        "-c", "--config",
        type=str,
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="1.0.0"
    )

    args = parser.parse_args()

    # Check if config file exists
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Warning: Config file not found: {config_path}")
        print("Using environment variables and defaults")
        config_path = None
    else:
        config_path = str(config_path)

    # Run application
    try:
        asyncio.run(main(config_path))
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    cli()
