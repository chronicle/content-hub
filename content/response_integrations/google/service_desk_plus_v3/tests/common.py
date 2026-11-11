from __future__ import annotations
import json
from integration_testing.common import get_def_file_content

import pathlib

from TIPCommon.types import SingleJson

from service_desk_plus_v3.core.datamodels import Request
from service_desk_plus_v3.core.ServiceDeskPlusV3Parser import ServiceDeskPlusV3Parser
from integration_testing.common import get_def_file_content

CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)
MOCK_PATH: pathlib.Path = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_DATA: SingleJson = get_def_file_content(MOCK_PATH)

parser: ServiceDeskPlusV3Parser = ServiceDeskPlusV3Parser()
REQUEST: Request = parser.build_request_object(MOCK_DATA["GET_REQUESTS_RESPONSE_FULL"])
ADD_REQUEST_MOCK: Request = parser.build_request_object(
    MOCK_DATA["ADD_REQUEST_SUCCESS_FULL"]
)
INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
