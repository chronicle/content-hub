from __future__ import annotations
import json
from integration_testing.common import get_def_file_content

import pathlib

from TIPCommon.types import SingleJson

import data_parser
from service_desk_plus.core.datamodels import WorkOrder
from integration_testing.common import get_def_file_content

CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)
MOCK_PATH: pathlib.Path = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_DATA: SingleJson = get_def_file_content(MOCK_PATH)

REQUEST: WorkOrder = data_parser.build_request(MOCK_DATA["GET_REQUESTS_RESPONSE_FULL"])
ADD_REQUEST_MOCK: WorkOrder = data_parser.build_request(
    MOCK_DATA["ADD_REQUEST_SUCCESS_FULL"]
)
INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
