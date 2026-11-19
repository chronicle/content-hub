from __future__ import annotations

import json
import pathlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson

TESTS_DIR: pathlib.Path = pathlib.Path(__file__).parent
INTEGRATION_PATH: pathlib.Path = TESTS_DIR.parent
CONFIG_PATH: pathlib.Path = TESTS_DIR / "config.json"
CONFIG: SingleJson = json.loads(CONFIG_PATH.read_text(encoding="utf-8")) if CONFIG_PATH.exists() else {}
