# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import json
import pathlib

import TIPCommon.encryption
from TIPCommon.data_models import DatabaseContextType
from TIPCommon.types import SingleJson

from zoho_desk.core.constants import (
    ACCESS_TOKEN_DB_KEY,
    ACTION_IDENTIFIER,
)
from zoho_desk.core.datamodels import Ticket
from integration_testing.common import get_def_file_content
from integration_testing.platform.external_context import ExternalContextRow


CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)

TOKEN_RECORD: str = json.dumps(
    {
        "expires_in": 999_999_999_999,
        "valid_until": 999_999_999_999,
        "token": TIPCommon.encryption.encrypt(
            data="1000.ac445cfb678764b9da88ac5024b767c5.ac445cfb678764b9da88ac5024b76",
            key=CONFIG["Client Secret"],
        ).decode(),
    }
)
EXPIRED_TOKEN_RECORD: str = json.dumps(
    {
        "expires_in": 0,
        "valid_until": 0,
        "token": TIPCommon.encryption.encrypt(
            data="1000.ac445cfb678764b9da88ac5024b767c5.ac445cfb678764b9da88ac5024b76",
            key=CONFIG["Client Secret"],
        ).decode(),
    }
)

ACCESS_TOKEN_DB_ROW: list[ExternalContextRow[str]] = [
    ExternalContextRow(
        context_type=DatabaseContextType.GLOBAL,
        identifier=ACTION_IDENTIFIER,
        property_key=ACCESS_TOKEN_DB_KEY,
        property_value=TOKEN_RECORD,
    )
]
EXPIRED_ACCESS_TOKEN_DB_ROW: list[ExternalContextRow[str]] = [
    ExternalContextRow(
        context_type=DatabaseContextType.GLOBAL,
        identifier=ACTION_IDENTIFIER,
        property_key=ACCESS_TOKEN_DB_KEY,
        property_value=EXPIRED_TOKEN_RECORD,
    )
]

DEFAULT_TICKET: Ticket = Ticket(
    raw_data={},
    id="Change ME",
    description="description",
    ticket_number="ticket_number",
    subject="subject",
    resolution="resolution",
    created_time=1_234_567_890,
    status="status",
    email="email@email.com",
    first_name="firstName",
    last_name="lastName",
)
INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
