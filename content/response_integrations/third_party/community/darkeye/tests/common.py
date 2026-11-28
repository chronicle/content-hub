from __future__ import annotations

import json
import pathlib
from typing import TYPE_CHECKING

from integration_testing.common import get_def_file_content

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
CONFIG_PATH: pathlib.Path = pathlib.Path.joinpath(INTEGRATION_PATH, "tests", "config.json")
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)
MOCKS_PATH: pathlib.Path = pathlib.Path.joinpath(INTEGRATION_PATH, "tests", "mocks")

HAVEIBEENRANSOM_ONLY_CONFIG: SingleJson = {**CONFIG, "Breach House API Key": ""}
BREACH_HOUSE_ONLY_CONFIG: SingleJson = {**CONFIG, "HaveIBeenRansom API Key": ""}
NO_KEY_CONFIG: SingleJson = {**CONFIG, "HaveIBeenRansom API Key": "", "Breach House API Key": ""}


def load_mock(name: str) -> SingleJson:
    return json.loads(pathlib.Path.joinpath(MOCKS_PATH, name).read_text(encoding="utf-8"))
