#!/usr/bin/env python3
"""Test Linear API integration."""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, '/home/von/agentic-todo')

from src.config import Config
from src.linear_client import LinearClient


async def test_linear():
    """Test Linear API functionality."""
    print("Testing Linear API Integration...\n")

    # Load config
    config = Config('/home/von/agentic-todo/config.yaml')

    retry_config = {
        "max_attempts": 3,
        "base_delay": 1.0,
        "max_delay": 60.0,
        "exponential_backoff": True
    }

    client = LinearClient(config.linear, retry_config)

    try:
        # Test 1: List existing issues
        print("1. Listing existing issues...")
        issues = await client.list_issues(limit=5)
        print(f"   ✓ Found {len(issues)} issues")
        for issue in issues[:3]:
            print(f"     - [{issue['identifier']}] {issue['title']}")

        # Test 2: Create a test issue
        print("\n2. Creating test issue...")
        new_issue = await client.create_issue(
            title="[TEST] Agentic Todo Integration Test",
            description="This is a test issue created by the Agentic Todo bot to verify API integration.",
            priority=0
        )
        print(f"   ✓ Created issue: {new_issue['identifier']}")
        print(f"     URL: {new_issue['url']}")

        # Test 3: Get the issue we just created
        print("\n3. Fetching created issue...")
        fetched = await client.get_issue(new_issue['id'])
        print(f"   ✓ Fetched: [{fetched['identifier']}] {fetched['title']}")

        # Test 4: Get workflow states
        print("\n4. Getting workflow states...")
        states = await client.get_workflow_states()
        print(f"   ✓ Found {len(states)} workflow states:")
        for state in states:
            print(f"     - {state['name']} ({state['type']})")

        print("\n" + "="*60)
        print("✅ All Linear API tests passed!")
        print("="*60)
        print(f"\nTest issue created: {new_issue['identifier']}")
        print(f"View it at: {new_issue['url']}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_linear())
