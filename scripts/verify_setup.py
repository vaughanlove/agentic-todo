#!/usr/bin/env python3
"""Verify that the agentic-todo system is properly configured."""

import os
import subprocess
import sys
from pathlib import Path


def check_python_version():
    """Check Python version."""
    version = sys.version_info
    if version < (3, 9):
        print("❌ Python 3.9+ required, found:", sys.version)
        return False
    print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
    return True


def check_signal_cli():
    """Check if signal-cli is installed."""
    try:
        result = subprocess.run(
            ["signal-cli", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✓ signal-cli installed: {version}")
            return True
        else:
            print("❌ signal-cli found but returned error")
            return False
    except FileNotFoundError:
        print("❌ signal-cli not found. Install from: https://github.com/AsamK/signal-cli")
        return False
    except Exception as e:
        print(f"❌ Error checking signal-cli: {e}")
        return False


def check_env_file():
    """Check if .env file exists and has required variables."""
    env_file = Path(".env")

    if not env_file.exists():
        print("❌ .env file not found. Copy .env.example to .env")
        return False

    print("✓ .env file exists")

    # Check for required variables
    required_vars = [
        "ANTHROPIC_API_KEY",
        "SIGNAL_PHONE_NUMBER",
    ]

    env_content = env_file.read_text()
    missing = []

    for var in required_vars:
        if var not in env_content or f"{var}=" not in env_content:
            missing.append(var)

    if missing:
        print(f"⚠️  Missing environment variables: {', '.join(missing)}")
        return False

    print("✓ Required environment variables present")
    return True


def check_config_file():
    """Check if config.yaml exists."""
    config_file = Path("config.yaml")

    if not config_file.exists():
        print("❌ config.yaml not found. Copy config.yaml.example to config.yaml")
        return False

    print("✓ config.yaml exists")
    return True


def check_dependencies():
    """Check if Python dependencies are installed."""
    try:
        import anthropic
        import pydantic
        import structlog
        import yaml

        print("✓ Core dependencies installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Run: pip install -r requirements.txt")
        return False


def check_logs_directory():
    """Check if logs directory exists."""
    logs_dir = Path("logs")

    if not logs_dir.exists():
        logs_dir.mkdir(parents=True, exist_ok=True)
        print("✓ Created logs directory")
    else:
        print("✓ Logs directory exists")

    return True


def main():
    """Run all checks."""
    print("\n" + "="*50)
    print("Agentic Todo - Setup Verification")
    print("="*50 + "\n")

    checks = [
        ("Python Version", check_python_version),
        ("signal-cli", check_signal_cli),
        ("Environment File", check_env_file),
        ("Config File", check_config_file),
        ("Dependencies", check_dependencies),
        ("Logs Directory", check_logs_directory),
    ]

    results = []
    for name, check_func in checks:
        print(f"\nChecking {name}...")
        results.append(check_func())

    print("\n" + "="*50)
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"✅ All checks passed ({passed}/{total})")
        print("\nYou're ready to run:")
        print("  python -m src.main")
        return 0
    else:
        print(f"⚠️  {passed}/{total} checks passed")
        print("\nPlease fix the issues above before running the application.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
