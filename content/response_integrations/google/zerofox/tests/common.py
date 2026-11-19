from __future__ import annotations
import json
from integration_testing.common import get_def_file_content
import os
import pathlib
import tempfile

from TIPCommon.types import SingleJson
from integration_testing.common import get_def_file_content


CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)
MOCK_PATH: pathlib.Path = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_DATA: SingleJson = get_def_file_content(MOCK_PATH)
LIST_ALERTS: SingleJson = MOCK_DATA["get_alerts"]
INVALID_TOKEN: SingleJson = MOCK_DATA["invalid_token"]
INVALID_ALERT: SingleJson = MOCK_DATA["invalid_alert"]
INVALID_CLOSE_ALERT: SingleJson = MOCK_DATA["invalid_close_alert"]
INVALID_ALERT_ID: int = 99999999

LIST_ALERTS_URL: str = "/1.0/alerts/"


def create_temp_file() -> str:
    """ Creates a temporary file with the given content and suffix.

    Returns:
        str: The file path.
    """
    content: bytes = b"fake file content"
    suffix: str = ".png"
    fd, temp_path = tempfile.mkstemp(suffix=suffix)
    temp_path = pathlib.Path(temp_path)
    with os.fdopen(fd, "wb") as temp_file:
        temp_file.write(content)

    return str(temp_path)


class AlertIdNotFoundError(Exception):
    """Accessed Alert ID cannot be found"""
INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
