from __future__ import annotations

import pathlib

INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
MOCKS_PATH = pathlib.Path.joinpath(INTEGRATION_PATH, "tests", "mocks")
