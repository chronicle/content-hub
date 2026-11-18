from __future__ import annotations

import sys
import sysconfig
from pathlib import Path

# On the Google SOAR platform environment, SDK modules (e.g. SiemplifyAddressProvider) are
# top-level imports. Locally they're bundled inside `soar_sdk/`, so we add that
# folder to sys.path to replicate the platform's import structure during tests.
_SOAR_SDK = Path(sysconfig.get_path("purelib")) / "soar_sdk"
if _SOAR_SDK.exists() and str(_SOAR_SDK) not in sys.path:
    sys.path.insert(0, str(_SOAR_SDK))

INTEGRATION_PATH: Path = Path(__file__).parent.parent
