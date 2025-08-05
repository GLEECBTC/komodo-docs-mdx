import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from lib.cli import command_handlers

def test_command_handlers_import():
    assert command_handlers is not None 