import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from lib.cli import doc_helper

def test_doc_helper_import():
    assert doc_helper is not None 