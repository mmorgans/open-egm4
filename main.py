#!/usr/bin/env python3
"""
He he he yup
"""

import argparse
from src.tui.app import main

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Open EGM-4 TUI")
    parser.add_argument("--force-unicode", action="store_true", help="Force usage of Unicode symbols even on Windows")
    args = parser.parse_args()
    main(force_unicode=args.force_unicode)
