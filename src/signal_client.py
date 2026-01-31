"""Signal-CLI client for sending and receiving messages."""

import asyncio
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from .config import SignalConfig
from .error_handler import ErrorSeverity, SignalError
from .utils.logger import get_logger
from .utils.retry import retry_decorator

logger = get_logger(__name__)


@dataclass
class SignalMessage:
    """Represents a Signal message."""

    sender: str
    recipient: str
    text: str
    timestamp: datetime
    group_id: Optional[str] = None
    attachments: List[str] = None

    def __post_init__(self):
        if self.attachments is None:
            self.attachments = []


class SignalClient:
    """Client for interacting with Signal via signal-cli."""

    def __init__(self, config: SignalConfig, retry_config: dict):
        """
        Initialize Signal client.

        Args:
            config: Signal configuration
            retry_config: Retry configuration dict
        """
        self.config = config
        self.retry_config = retry_config
        self.logger = get_logger(__name__)

    async def _run_signal_command(
        self,
        args: List[str],
        timeout: float = 30.0,
        json_output: bool = False
    ) -> str:
        """
        Run a signal-cli command.

        Args:
            args: Command arguments
            timeout: Command timeout in seconds
            json_output: Use JSON output format

        Returns:
            Command output

        Raises:
            SignalError: If command fails
        """
        # Build command with JSON output flag if requested
        cmd = [self.config.cli_path]
        if json_output:
            cmd.extend(["--output", "json"])
        cmd.extend(["-a", self.config.account])
        cmd.extend(args)

        try:
            self.logger.debug("Running signal-cli command", command=cmd)

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                raise SignalError(
                    f"Signal command timed out after {timeout}s",
                    severity=ErrorSeverity.MEDIUM,
                    context={"command": args}
                )

            if process.returncode != 0:
                error_msg = stderr.decode('utf-8').strip()
                raise SignalError(
                    f"Signal command failed: {error_msg}",
                    severity=ErrorSeverity.MEDIUM,
                    context={
                        "command": args,
                        "return_code": process.returncode,
                        "stderr": error_msg
                    }
                )

            output = stdout.decode('utf-8').strip()
            self.logger.debug("Signal command completed", output_length=len(output))
            return output

        except FileNotFoundError:
            raise SignalError(
                f"signal-cli not found at {self.config.cli_path}",
                severity=ErrorSeverity.HIGH,
                user_message="Signal is not properly installed. Please install signal-cli.",
                context={"cli_path": self.config.cli_path}
            )
        except Exception as e:
            if isinstance(e, SignalError):
                raise
            raise SignalError(
                f"Failed to execute signal-cli command: {str(e)}",
                severity=ErrorSeverity.MEDIUM,
                original_error=e,
                context={"command": args}
            )

    @retry_decorator(max_attempts=3, base_delay=1.0, exponential_backoff=True)
    async def send_message(
        self,
        recipient: str,
        message: str,
        group_id: Optional[str] = None
    ) -> bool:
        """
        Send a message via Signal.

        Args:
            recipient: Recipient phone number or group ID
            message: Message text
            group_id: Group ID if sending to a group

        Returns:
            True if message sent successfully

        Raises:
            SignalError: If message sending fails
        """
        try:
            args = ["send", "-m", message]

            if group_id:
                args.extend(["-g", group_id])
            else:
                args.append(recipient)

            await self._run_signal_command(args)

            self.logger.info(
                "Message sent successfully",
                recipient=recipient,
                group_id=group_id,
                message_length=len(message)
            )
            return True

        except Exception as e:
            self.logger.error(
                "Failed to send message",
                recipient=recipient,
                error=str(e)
            )
            raise

    async def receive_messages(self, timeout: float = 1.0) -> List[SignalMessage]:
        """
        Receive new messages from Signal.

        Args:
            timeout: Receive timeout in seconds

        Returns:
            List of received messages

        Raises:
            SignalError: If receiving fails
        """
        try:
            # Pass timeout to signal-cli and add buffer for subprocess timeout
            output = await self._run_signal_command(
                ["receive", "-t", str(int(timeout))],
                timeout=timeout + 5.0,  # Add 5 second buffer for subprocess
                json_output=True
            )

            if not output:
                return []

            messages = []
            for line in output.split('\n'):
                if not line.strip():
                    continue

                try:
                    data = json.loads(line)
                    envelope = data.get('envelope', {})

                    # Check if it's a data message
                    data_message = envelope.get('dataMessage')
                    if not data_message:
                        continue

                    message_text = data_message.get('message', '')
                    if not message_text:
                        continue

                    message = SignalMessage(
                        sender=envelope.get('source', ''),
                        recipient=self.config.account,
                        text=message_text,
                        timestamp=datetime.fromtimestamp(
                            envelope.get('timestamp', 0) / 1000
                        ),
                        group_id=data_message.get('groupInfo', {}).get('groupId')
                    )
                    messages.append(message)

                except json.JSONDecodeError as e:
                    self.logger.warning(
                        "Failed to parse message JSON",
                        line=line,
                        error=str(e)
                    )
                    continue

            if messages:
                self.logger.info(f"Received {len(messages)} new messages")

            return messages

        except SignalError:
            raise
        except Exception as e:
            raise SignalError(
                f"Failed to receive messages: {str(e)}",
                severity=ErrorSeverity.MEDIUM,
                original_error=e
            )

    async def send_error_notification(
        self,
        recipient: str,
        error_message: str
    ) -> None:
        """
        Send an error notification to a user.

        Args:
            recipient: Recipient phone number
            error_message: Error message to send
        """
        try:
            await self.send_message(recipient, error_message)
        except Exception as e:
            self.logger.error(
                "Failed to send error notification",
                recipient=recipient,
                error=str(e)
            )
