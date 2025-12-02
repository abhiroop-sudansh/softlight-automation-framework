#!/usr/bin/env python3
"""
Tutorial Generator CLI - Main entry point.

This is the interface for Agent A to request tutorials from Agent B.

Usage:
    python tutorial_cli.py capture "How do I create a project in Linear?"
    python tutorial_cli.py interactive
    python tutorial_cli.py examples
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from softlight_automation_framework.tutorial.cli import main

if __name__ == "__main__":
    main()

