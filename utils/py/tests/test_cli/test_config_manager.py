import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from lib.cli import config_manager

def test_config_manager_import():
    assert config_manager is not None 