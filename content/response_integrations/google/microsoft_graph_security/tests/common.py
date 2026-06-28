from __future__ import annotations

import pathlib

from TIPCommon.types import SingleJson
import json

def get_json_file_content(path: pathlib.Path) -> SingleJson:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_json_file_content(CONFIG_PATH)
MOCK_PATH: pathlib.Path = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_DATA: SingleJson = get_json_file_content(MOCK_PATH)
INCIDENT = MOCK_DATA.get("incident")
LIST_INCIDENTS = MOCK_DATA.get("list_incidents")
