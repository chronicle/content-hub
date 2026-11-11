from __future__ import annotations
import json
from integration_testing.common import get_def_file_content
import pathlib


CONFIG_FILE: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / 'config.json'
CONFIG: dict = get_def_file_content(CONFIG_PATH) if CONFIG_PATH.exists() else {}
