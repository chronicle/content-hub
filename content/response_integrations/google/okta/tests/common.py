from __future__ import annotations
from integration_testing.common import get_def_file_content
import pathlib
import json

from TIPCommon.types import SingleJson


CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"


def get_json_file_content(json_file_path: str | pathlib.Path | None) -> SingleJson:
    """Get the content of a json file"""

    if isinstance(json_file_path, str):
        json_file_path: pathlib.Path = pathlib.Path(json_file_path)

    return json.loads(json_file_path.read_text(encoding="utf-8"))
INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
CONFIG: dict = get_def_file_content(CONFIG_PATH) if CONFIG_PATH.exists() else {}
