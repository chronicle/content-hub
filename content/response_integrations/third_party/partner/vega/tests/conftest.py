from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# TIPCommon.types imports bare Siemplify* modules; expose soar_sdk the same way
# the marketplace runtime does.
try:
    import soar_sdk
except ImportError:
    soar_sdk = None
else:
    soar_sdk_dir = str(Path(soar_sdk.__file__).resolve().parent)
    if soar_sdk_dir not in sys.path:
        sys.path.insert(0, soar_sdk_dir)
