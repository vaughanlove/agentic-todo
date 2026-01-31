#!/usr/bin/env python3
"""Test the new Vonnegut-style response formatting."""

import asyncio
import sys

sys.path.insert(0, '/home/von/agentic-todo')

from src.config import Config
from src.claude_client import ClaudeClient


async def test_responses():
    """Test different response styles."""
    print("\n" + "="*60)
    print("Testing Vonnegut-Style Responses")
    print("="*60 + "\n")

    config = Config('/home/von/agentic-todo/config.yaml')
    retry_config = {
        "max_attempts": 3,
        "base_delay": 1.0,
        "max_delay": 60.0,
        "exponential_backoff": True
    }

    client = ClaudeClient(config.claude, retry_config)

    test_messages = [
        "Create a task to fix the login bug",
        "Show me my current tasks",
        "What do I need to work on?",
    ]

    for msg in test_messages:
        print(f"User: {msg}")
        print("-" * 60)

        try:
            response = await client.process_message(
                user_message=msg,
                conversation_history=[],
                context={"user_tasks": [
                    {"identifier": "AGE-1", "title": "Get familiar with Linear", "state": "Todo"},
                    {"identifier": "AGE-4", "title": "Import your data", "state": "In Progress"},
                    {"identifier": "AGE-5", "title": "Test integration", "state": "Done"}
                ]}
            )

            print(f"Bot: {response}")
            print()

        except Exception as e:
            print(f"Error: {e}\n")

    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_responses())
