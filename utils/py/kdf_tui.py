#!/usr/bin/env python3
"""
KDF Tools TUI Wrapper

Simple wrapper to launch the KDF Tools TUI interface.
"""

import sys
from pathlib import Path

# Add the project root to Python path
_script_dir = Path(__file__).parent
_workspace_root = _script_dir.parent.parent
sys.path.insert(0, str(_workspace_root))

try:
    from lib.tui.kdf_tui import main
    main()
except ImportError as e:
    print(f"Error importing TUI components: {e}")
    print("Please ensure all dependencies are installed:")
    print("pip install textual rich")
    sys.exit(1)
except Exception as e:
    print(f"Error starting TUI: {e}")
    sys.exit(1) 