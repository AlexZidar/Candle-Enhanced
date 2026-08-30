#!/usr/bin/env python3
"""Candle GRBL Controller - Application Entry Point."""

import sys
import os

# Ensure the package root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from candle.main import main

if __name__ == "__main__":
    sys.exit(main())
