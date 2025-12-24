from __future__ import annotations

import json
import pathlib

INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
CONFIG_PATH = pathlib.Path.joinpath(INTEGRATION_PATH, "tests", "config.json")

TEST_BOT_TOKEN = json.loads(CONFIG_PATH.read_text(encoding="utf-8")).get(
    "API TOKEN", "test_bot_token"
)
