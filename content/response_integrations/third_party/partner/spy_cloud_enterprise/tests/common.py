from __future__ import annotations

import pathlib

INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
CONFIG_PATH = INTEGRATION_PATH / "tests" / "config.json"
