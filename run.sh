#!/bin/bash
# Easy runner for Softlight Automation Framework
cd "$(dirname "$0")"
./venv/bin/python3 run_agent.py "$@"

