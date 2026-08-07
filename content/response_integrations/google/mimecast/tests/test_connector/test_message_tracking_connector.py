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

import copy
import pathlib
import sys

from TIPCommon.data_models import DatabaseContextType
from TIPCommon.types import SingleJson
from TIPCommon.utils import is_test_run

from ...connectors import MessageTrackingConnector
from ...core.datamodels import (
    Attachment,
    HoldMessage,
    Message,
    MessageDetails,
)
from ...tests.core.session import MimecastSession
from ...tests.common import (
    ATTACHMENT,
    CONFIG,
    HOLD_MESSAGE,
    INTEGRATION_PATH,
    MESSAGE,
    MESSAGE_DETAILS,
)
from ...tests.core.product import Mimecast
from integration_testing.common import set_is_test_run_to_true, set_is_test_run_to_false
from integration_testing.platform.script_output import MockConnectorOutput
from integration_testing.set_meta import set_metadata
from integration_testing.platform.external_context import (
    ExternalContextRowKey,
    MockExternalContext,
)

IDS_DB_KEY: str = "offset"
DEF_PATH: pathlib.Path = pathlib.Path(__file__).parent / "mock_message_tracking_connector.json"

DEFAULT_PARAMETERS: SingleJson = {
    "Environment": "Default Environment",
    "Run Every": 10,
    "DeviceProductField": "Product Name",
    "EventClassId": "event_type",
    "Environment Field Name": "",
    "Environment Regex Pattern": "",
    "PythonProcessTimeout": "180",
    "API Root": CONFIG.get("API Root"),
    "Application Key": CONFIG.get("Application Key"),
    "Application ID": CONFIG.get("Application ID"),
    "Access Key": CONFIG.get("Access Key"),
    "Secret Key": CONFIG.get("Refresh Token"),
    "Client ID": CONFIG.get("Client ID"),
    "Client Secret": CONFIG.get("Client Secret"),
    "Domains": "xyz.com",
    "Max Messages To Return": 20,
    "Lowest Risk To Fetch": "",
    "Status Filter": "held",
    "Route Filter": "",
    "Queue Reason Filter": "Fraud Alert",
    "Ingest Messages Without Risk": "true",
    "Max Hours Backwards": "1",
    "Use whitelist as a blacklist": "false",
    "Verify SSL": "false",
}
ALERT_NAME: str = "Held Message"


@set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
def test_message_tracking_connector(
    mimecast: Mimecast,
    script_session: MimecastSession,
    connector_output: MockConnectorOutput,
) -> None:
    # Arrange
    message_1: Message = copy.deepcopy(MESSAGE)
    message_1.tracking_id = "Test_Id_3"
    message_1.received = "2025-04-16T16:07:14+0000"
    message_1.raw_data["id"] = message_1.tracking_id
    message_1.raw_data["received"] = message_1.received
    message_details_1: MessageDetails = copy.deepcopy(MESSAGE_DETAILS)
    message_details_1.tracking_id = "Test_Id_3"
    message_details_1.reason = "fraud alert"
    message_details_1.sent = "2025-04-16T15:32:49+0000"
    message_details_1.raw_data["id"] = message_details_1.tracking_id
    message_details_1.raw_data["recipientInfo"]["messageInfo"]["sent"] = (
        message_details_1.sent
    )
    message_details_1.raw_data["queueInfo"]["reason"] = message_details_1.reason
    hold_message_1: HoldMessage = copy.deepcopy(HOLD_MESSAGE)
    hold_message_1.message_id = "Test_Id_1"
    hold_message_1.subject = "TestSubject"
    hold_message_1.sender = "TestSender"
    hold_message_1.raw_data["id"] = hold_message_1.message_id
    hold_message_1.raw_data["subject"] = hold_message_1.subject
    hold_message_1.raw_data["sender"] = hold_message_1.sender
    attachment_1: Attachment = copy.deepcopy(ATTACHMENT)
    attachment_1.attachment_id = "attachment_id_1"
    attachment_1.raw_data["id"] = attachment_1.attachment_id
    mimecast.add_message(message_1)
    mimecast.add_message_details(message_details_1)
    mimecast.add_hold_message(hold_message_1)
    mimecast.add_attachment(attachment_1)

    set_is_test_run_to_true()
    is_test = is_test_run(sys.argv)
    MessageTrackingConnector.main(is_test)

    assert len(script_session.request_history) == 9
    assert connector_output.results.json_output.alerts[0].name == ALERT_NAME


@set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
def test_microsoft_graph_mail_connector_with_no_external_context(
    mimecast: Mimecast,
    script_session: MimecastSession,
    connector_output: MockConnectorOutput,
    external_context: MockExternalContext,
) -> None:
    # Arrange
    message_1: Message = copy.deepcopy(MESSAGE)
    message_1.tracking_id = "Test_Id_3"
    message_1.received = "2025-04-16T16:07:14+0000"
    message_1.raw_data["id"] = message_1.tracking_id
    message_1.raw_data["received"] = message_1.received
    message_2: Message = copy.deepcopy(MESSAGE)
    message_2.tracking_id = "Test_Id_4"
    message_2.received = "2025-04-16T18:07:14+0000"
    message_2.raw_data["id"] = message_2.tracking_id
    message_2.raw_data["received"] = message_2.received
    message_details_1: MessageDetails = copy.deepcopy(MESSAGE_DETAILS)
    message_details_1.tracking_id = "Test_Id_3"
    message_details_1.reason = "fraud alert"
    message_details_1.sent = "2025-04-16T15:32:49+0000"
    message_details_1.raw_data["id"] = message_details_1.tracking_id
    message_details_1.raw_data["recipientInfo"]["messageInfo"]["sent"] = (
        message_details_1.sent
    )
    message_details_1.raw_data["queueInfo"]["reason"] = message_details_1.reason
    message_details_2: MessageDetails = copy.deepcopy(MESSAGE_DETAILS)
    message_details_2.tracking_id = "Test_Id_4"
    message_details_2.reason = "fraud alert"
    message_details_2.sent = "2025-04-16T18:32:49+0000"
    message_details_2.raw_data["id"] = message_details_2.tracking_id
    message_details_2.raw_data["recipientInfo"]["messageInfo"]["sent"] = (
        message_details_2.sent
    )
    message_details_2.raw_data["queueInfo"]["reason"] = message_details_2.reason
    hold_message_1: HoldMessage = copy.deepcopy(HOLD_MESSAGE)
    hold_message_1.message_id = "Test_Id_1"
    hold_message_1.subject = "TestSubject"
    hold_message_1.sender = "TestSender"
    hold_message_1.raw_data["id"] = hold_message_1.message_id
    hold_message_1.raw_data["subject"] = hold_message_1.subject
    hold_message_1.raw_data["sender"] = hold_message_1.sender

    attachment_1: Attachment = copy.deepcopy(ATTACHMENT)
    attachment_2: Attachment = copy.deepcopy(ATTACHMENT)
    attachment_1.attachment_id = "attachment_id_1"
    attachment_2.attachment_id = "attachment_id_2"
    attachment_1.raw_data["id"] = attachment_1.attachment_id
    attachment_2.raw_data["id"] = attachment_2.attachment_id
    mimecast.add_message(message_1)
    mimecast.add_message(message_2)
    mimecast.add_message_details(message_details_1)
    mimecast.add_message_details(message_details_2)
    mimecast.add_hold_message(hold_message_1)
    mimecast.add_attachment(attachment_1)
    mimecast.add_attachment(attachment_2)

    set_is_test_run_to_false()
    is_test = is_test_run(sys.argv)
    MessageTrackingConnector.main(is_test)

    assert len(script_session.request_history) == 31
    assert connector_output.results.json_output.alerts[0].name == ALERT_NAME
    assert len(connector_output.results.json_output.alerts) == 4

    row_key: ExternalContextRowKey = ExternalContextRowKey(
        context_type=DatabaseContextType.CONNECTOR,
        property_key=IDS_DB_KEY,
        identifier=None,
    )
    assert row_key not in external_context
