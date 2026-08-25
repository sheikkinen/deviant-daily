#!/usr/bin/env python
"""Operator entry point for FR-889 user-prompt generation.

Usage:
    python scripts/generate.py --prompt "text" [--model name]
        [--date YYYY-MM-DD] [--out-dir dir]
    python scripts/generate.py --prompt-file path ...
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.user_generate import main  # noqa: E402

if __name__ == "__main__":
    main()
