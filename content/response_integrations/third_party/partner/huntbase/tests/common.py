from __future__ import annotations

import pathlib

from integration_testing.common import get_def_file_content

INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
CONFIG_PATH: pathlib.Path = INTEGRATION_PATH / "tests" / "config.json"
CONFIG: dict = get_def_file_content(CONFIG_PATH)
CONNECTOR_DEF_PATH: pathlib.Path = INTEGRATION_PATH / "connectors" / "huntbase_findings_connector.yaml"
API_ROOT: str = CONFIG["API Root"]
APP_ROOT: str = API_ROOT.removesuffix("/api/v1")
