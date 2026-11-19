from __future__ import annotations
import json
from integration_testing.common import get_def_file_content
import pathlib

from TIPCommon.types import SingleJson

from integration_testing.common import get_def_file_content


CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)
INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
