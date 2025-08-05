#!/bin/bash

# Activate the virtual environment
source utils/py/.venv/bin/activate

# Run the pytest command with debug logging
pytest -s -o log_cli=true -o log_cli_level=DEBUG utils/py/kdf_test_cases/test_kdf_methods.py

