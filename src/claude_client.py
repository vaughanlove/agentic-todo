"""Claude API client for AI-powered task management."""

from typing import Any, Dict, List, Optional

from anthropic import Anthropic, AsyncAnthropic

from .config import ClaudeConfig
from .error_handler import ClaudeError, ErrorSeverity
from .utils.logger import get_logger
from .utils.retry import retry_decorator

logger = get_logger(__name__)


class ClaudeClient:
    """Client for interacting with Claude AI."""

    def __init__(self, config: ClaudeConfig, retry_config: dict):
        """
        Initialize Claude client.

        Args:
            config: Claude configuration
            retry_config: Retry configuration dict
        """
        self.config = config
        self.retry_config = retry_config
        self.logger = get_logger(__name__)

        if not config.api_key:
            raise ClaudeError(
                "Anthropic API key is required",
                severity=ErrorSeverity.CRITICAL,
                user_message="AI assistant is not configured. Please set ANTHROPIC_API_KEY."
            )

        self.client = AsyncAnthropic(api_key=config.api_key)

    @retry_decorator(max_attempts=3, base_delay=2.0, exponential_backoff=True)
    async def process_message(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Process a user message and generate a response.

        Args:
            user_message: The user's message
            conversation_history: Previous conversation messages
            context: Additional context (e.g., Linear tasks, user info)

        Returns:
            Claude's response text

        Raises:
            ClaudeError: If API call fails
        """
        try:
            # Build messages array
            messages = []

            # Add conversation history if provided
            if conversation_history:
                messages.extend(conversation_history)

            # Add current user message
            messages.append({
                "role": "user",
                "content": user_message
            })

            # Build system prompt with context
            system_prompt = self.config.system_prompt

            if context:
                system_prompt += self._format_context(context)

            self.logger.info(
                "Sending message to Claude",
                message_length=len(user_message),
                history_length=len(conversation_history) if conversation_history else 0
            )

            # Call Claude API
            response = await self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=system_prompt,
                messages=messages
            )

            # Extract response text
            response_text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    response_text += block.text

            self.logger.info(
                "Received response from Claude",
                response_length=len(response_text),
                stop_reason=response.stop_reason
            )

            return response_text.strip()

        except Exception as e:
            error_msg = str(e)

            # Check for rate limiting
            if "rate_limit" in error_msg.lower() or "429" in error_msg:
                raise ClaudeError(
                    f"Rate limit exceeded: {error_msg}",
                    severity=ErrorSeverity.MEDIUM,
                    user_message="AI assistant is receiving too many requests. Please try again in a moment.",
                    original_error=e
                )

            # Check for authentication errors
            if "authentication" in error_msg.lower() or "401" in error_msg:
                raise ClaudeError(
                    f"Authentication failed: {error_msg}",
                    severity=ErrorSeverity.CRITICAL,
                    user_message="AI assistant authentication failed. Please check configuration.",
                    original_error=e
                )

            # Generic error
            raise ClaudeError(
                f"Failed to process message with Claude: {error_msg}",
                severity=ErrorSeverity.HIGH,
                original_error=e,
                context={"message_length": len(user_message)}
            )

    def _format_context(self, context: Dict[str, Any]) -> str:
        """
        Format context information for the system prompt.

        Args:
            context: Context dictionary

        Returns:
            Formatted context string
        """
        context_parts = ["\n\nAdditional Context:"]

        if "user_tasks" in context:
            tasks = context["user_tasks"]
            if tasks:
                context_parts.append(f"\n\nUser's Current Tasks ({len(tasks)}):")
                for task in tasks[:10]:  # Limit to 10 tasks
                    title = task.get("title", "Untitled")
                    # Handle both dict and string formats for state
                    state = task.get("state", "Unknown")
                    if isinstance(state, dict):
                        state = state.get("name", "Unknown")
                    identifier = task.get("identifier", "")
                    context_parts.append(f"- [{identifier}] {title} ({state})")

        if "user_info" in context:
            user_info = context["user_info"]
            if "name" in user_info:
                context_parts.append(f"\n\nUser: {user_info['name']}")

        if "workspace_info" in context:
            workspace = context["workspace_info"]
            if "name" in workspace:
                context_parts.append(f"Workspace: {workspace['name']}")

        return "\n".join(context_parts) if len(context_parts) > 1 else ""

    async def extract_task_info(self, message: str) -> Dict[str, Any]:
        """
        Extract task information from a natural language message.

        Args:
            message: User's message

        Returns:
            Extracted task information

        Raises:
            ClaudeError: If extraction fails
        """
        try:
            system_prompt = """You are a task extraction assistant. Extract task information from user messages.

Return a JSON object with these fields:
- action: "create", "update", "list", "search", or "complete"
- title: task title (if creating)
- description: task description (if available)
- priority: "urgent", "high", "normal", or "low" (if mentioned)
- assignee: assignee name (if mentioned)

Examples:
"Create a task to fix the login bug" -> {"action": "create", "title": "Fix the login bug", "priority": "normal"}
"Mark task ENG-123 as done" -> {"action": "complete", "identifier": "ENG-123"}
"Show me my urgent tasks" -> {"action": "list", "priority": "urgent"}
"""

            response = await self.client.messages.create(
                model=self.config.model,
                max_tokens=1024,
                temperature=0.3,
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": f"Extract task info from: {message}"
                }]
            )

            # Parse response
            response_text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    response_text += block.text

            # TODO: Parse JSON from response
            # For now, return a simple structure
            return {
                "action": "create",
                "raw_message": message
            }

        except Exception as e:
            raise ClaudeError(
                f"Failed to extract task info: {str(e)}",
                severity=ErrorSeverity.MEDIUM,
                original_error=e
            )
