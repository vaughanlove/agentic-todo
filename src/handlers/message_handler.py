"""Core message handler for processing user messages."""

from typing import Any, Dict, Optional

from ..claude_client import ClaudeClient
from ..error_handler import ErrorHandler
from ..linear_client import LinearClient
from ..queue_manager import QueuedMessage
from ..signal_client import SignalClient
from ..utils.logger import get_logger

logger = get_logger(__name__)


class MessageHandler:
    """Handles incoming messages and coordinates responses."""

    def __init__(
        self,
        signal_client: SignalClient,
        linear_client: LinearClient,
        claude_client: ClaudeClient,
        error_handler: ErrorHandler
    ):
        """
        Initialize message handler.

        Args:
            signal_client: Signal client
            linear_client: Linear client
            claude_client: Claude client
            error_handler: Error handler
        """
        self.signal_client = signal_client
        self.linear_client = linear_client
        self.claude_client = claude_client
        self.error_handler = error_handler
        self.logger = get_logger(__name__)

        # Store conversation history per user
        self.conversations: Dict[str, list] = {}

    async def handle(self, message: QueuedMessage) -> str:
        """
        Handle a queued message.

        Args:
            message: Queued message to process

        Returns:
            Response message
        """
        sender = message.sender
        text = message.text

        self.logger.info(
            "Handling message",
            message_id=message.id,
            sender=sender,
            text_length=len(text)
        )

        try:
            # Get conversation history for this user
            history = self.conversations.get(sender, [])

            # Get user's Linear tasks for context
            context = await self._build_context(sender)

            # Process with Claude
            response = await self.claude_client.process_message(
                user_message=text,
                conversation_history=history,
                context=context
            )

            # Update conversation history
            history.append({"role": "user", "content": text})
            history.append({"role": "assistant", "content": response})

            # Keep only last 10 messages
            if len(history) > 20:
                history = history[-20:]

            self.conversations[sender] = history

            # Check if Claude wants to perform an action
            action = await self._extract_action(response, text)

            final_response = response
            if action:
                # Execute action and get formatted result
                action_result = await self._execute_action(action, sender)
                if action_result:
                    # Replace any technical details with user-friendly message
                    final_response = self._clean_response(response, action_result)

            # Send response
            await self.signal_client.send_message(sender, final_response)

            self.logger.info(
                "Message handled successfully",
                message_id=message.id,
                response_length=len(response)
            )

            return response

        except Exception as e:
            self.logger.error(
                "Error handling message",
                message_id=message.id,
                error=str(e),
                error_type=type(e).__name__
            )

            # Handle error and get user-friendly message
            error_message = await self.error_handler.handle_error(
                error,
                context={"message_id": message.id, "sender": sender},
                user_id=sender
            )

            # Send error notification to user
            if error_message:
                await self.signal_client.send_error_notification(
                    sender,
                    error_message
                )

            raise

    async def _build_context(self, sender: str) -> Dict[str, Any]:
        """
        Build context for Claude (user tasks, etc.).

        Args:
            sender: Message sender

        Returns:
            Context dictionary
        """
        context = {}

        try:
            # Get user's tasks from Linear
            # In production, you would filter by assignee
            tasks = await self.linear_client.list_issues(limit=10)

            # Format tasks in a simple way for Claude
            formatted_tasks = []
            for task in tasks:
                formatted_tasks.append({
                    "identifier": task.get("identifier"),
                    "title": task.get("title"),
                    "state": task.get("state", {}).get("name", "Unknown"),
                    "priority": task.get("priority", 0)
                })

            context["user_tasks"] = formatted_tasks

        except Exception as e:
            self.logger.warning(
                "Failed to fetch user tasks for context",
                error=str(e)
            )

        return context

    async def _extract_action(
        self,
        response: str,
        original_message: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract action to perform from Claude's response.

        Args:
            response: Claude's response
            original_message: Original user message

        Returns:
            Action dictionary or None
        """
        # Check if response indicates an action
        # In production, use structured output or tool use
        action_keywords = {
            "create": ["creating task", "created task", "i'll create"],
            "update": ["updating task", "updated task", "i'll update"],
            "complete": ["marking as complete", "marked as complete", "completed"],
        }

        for action_type, keywords in action_keywords.items():
            if any(keyword in response.lower() for keyword in keywords):
                return {
                    "type": action_type,
                    "message": original_message,
                    "response": response
                }

        return None

    async def _execute_action(
        self,
        action: Dict[str, Any],
        sender: str
    ) -> Optional[Dict[str, Any]]:
        """
        Execute an action (create task, etc.).

        Args:
            action: Action dictionary
            sender: Message sender

        Returns:
            Action result with user-friendly details
        """
        action_type = action["type"]

        self.logger.info("Executing action", action_type=action_type, sender=sender)

        try:
            if action_type == "create":
                # Extract task info from message
                task_info = await self.claude_client.extract_task_info(
                    action["message"]
                )

                # Create task in Linear
                issue = await self.linear_client.create_issue(
                    title=task_info.get("title", action["message"][:100]),
                    description=action["message"]
                )

                self.logger.info(
                    "Task created",
                    issue_id=issue["id"],
                    identifier=issue.get("identifier")
                )

                return {
                    "type": "create",
                    "identifier": issue.get("identifier"),
                    "title": issue.get("title"),
                    "url": issue.get("url")
                }

            elif action_type == "update":
                # TODO: Implement update logic
                pass

            elif action_type == "complete":
                # TODO: Implement completion logic
                pass

            return None

        except Exception as e:
            self.logger.error(
                "Failed to execute action",
                action_type=action_type,
                error=str(e)
            )
            return None

    def _clean_response(self, response: str, action_result: Dict[str, Any]) -> str:
        """
        Clean Claude's response to remove technical details and add action results.

        Args:
            response: Original Claude response
            action_result: Result from action execution

        Returns:
            Cleaned, user-friendly response
        """
        # Remove common technical patterns
        import re

        # Remove XML-like tags
        cleaned = re.sub(r'<[^>]+>', '', response)

        # Remove JSON-like structures
        cleaned = re.sub(r'\{[^}]+\}', '', cleaned)

        # Remove API-like responses
        cleaned = re.sub(r'```[\s\S]*?```', '', cleaned)

        # If we have action results, append them nicely
        if action_result:
            if action_result["type"] == "create":
                # Append task identifier to response
                if action_result["identifier"] not in cleaned:
                    cleaned = f"{cleaned}\n\nTask created: {action_result['identifier']}"

        # Clean up extra whitespace
        cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)
        cleaned = cleaned.strip()

        return cleaned
