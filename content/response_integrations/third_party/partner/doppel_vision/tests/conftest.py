from __future__ import annotations

import sys
from pathlib import Path

import soar_sdk

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SDK_ROOT = str(Path(soar_sdk.__file__).parent)
if SDK_ROOT not in sys.path:
    sys.path.insert(0, SDK_ROOT)
