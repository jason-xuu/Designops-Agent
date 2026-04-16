"""Shared pytest configuration.

Adds the project root to ``sys.path`` so tests can import ``src.*`` without
requiring an editable install, and defaults LLM_PROVIDER to "none" during
test runs so nothing unexpectedly hits Ollama.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("LLM_PROVIDER", "none")
