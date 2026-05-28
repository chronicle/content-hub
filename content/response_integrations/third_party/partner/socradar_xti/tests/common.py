from __future__ import annotations

import json
import pathlib

INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: dict = json.loads(CONFIG_PATH.read_text()) if CONFIG_PATH.exists() else {}
