from __future__ import annotations

import pathlib

INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
CONFIG_PATH = pathlib.Path.joinpath(INTEGRATION_PATH, "tests", "config.json")
MOCKS_PATH = pathlib.Path.joinpath(INTEGRATION_PATH, "tests", "mocks")
