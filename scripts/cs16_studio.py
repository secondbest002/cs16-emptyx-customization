#!/usr/bin/env python3
"""
scripts/cs16_studio.py - Top-level entry point for CS 1.6 Asset Studio & EmptyX Customization.
"""

import os
import sys
from pathlib import Path

# Ensure package directory is on Python path
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from cs16_studio.cli import main

if __name__ == "__main__":
    main()
