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

import pathlib
import json

from TIPCommon.data_models import DatabaseContextType
from TIPCommon.types import SingleJson
from TIPCommon.consts import IDS_DB_KEY

from ..connectors.PubSubMessagesConnector import (
    PubSubMessagesConnector,
)
from ..tests.common import INTEGRATION_PATH, MOCK_DATA, CONFIG
from ..tests.core.session import ApiSession
from ..tests.core.product import Product
from ..tests.utils import (
    assert_get_subscription,
    assert_pull_messages,
    assert_ack_messages,
)
from integration_testing.common import set_is_test_run_to_true, set_is_test_run_to_false
from integration_testing.platform.external_context import ExternalContextRowKey
from integration_testing.platform.external_context import MockExternalContext
from integration_testing.platform.script_output import MockConnectorOutput
from integration_testing.set_meta import set_metadata


DEF_PATH: pathlib.Path = pathlib.Path(__file__).parent / "mock_pub_sub_messages_connector.json"
DEFAULT_PARAMETERS: SingleJson = {
    "DeviceProductField": "alert_type",
    "EventClassId": "event_type",
    "Workload Identity Email": "gcloud-pubsub@test-project.iam.gserviceaccount.com",
    "Project ID": "test-project",
    "Quota Project ID": "test-quota-project",
    "User Service Account JSON Secret": None,
    "Max Messages To Fetch": 100,
    "Subscription ID": "test-sub",
    "Timestamp Field": "message_publishTime",
    "Timestamp Format": "%Y-%m-%dT%H:%M:%S.%fZ",
    "Alert Name Template": "Alert from [message_json_notificationConfigName]",
    "Rule Generator Template": "Rule [message_json_finding_category]",
    "Severity Mapping JSON": "{\"Default\": 60}",
    "Verify SSL": True,
    "Unique ID Field": "message_id",
    "Case Name Template": "Alert from [message_json_notificationConfigName]",
    "Environment Field Name": "env_field",
    "Environment Regex Pattern": ".*"
}
TEST_CONNECTOR_IDENTIFIER = "test_connector_identifier"


class TestTestRun:
    @set_metadata(
            connector_def_file_path=DEF_PATH,
            parameters=DEFAULT_PARAMETERS,
            integration_config=CONFIG,
            input_context={"integrationContext": CONFIG}
    )
    def test_connector_test_run_no_messages(
            self,
            gcloud_pubsub_script_session: ApiSession,
            connector_output: MockConnectorOutput,
    ) -> None:
        set_is_test_run_to_true()
        connector = PubSubMessagesConnector()
        connector.siemplify.context.connector_info.identifier = (
            TEST_CONNECTOR_IDENTIFIER
        )
        connector.start()

        assert connector_output.results.json_output.alerts == []
        assert len(gcloud_pubsub_script_session.request_history) == 3
        assert_get_subscription(gcloud_pubsub_script_session.request_history, 1)
        assert_pull_messages(gcloud_pubsub_script_session.request_history, 2)


class TestConnectorExternalContext:
    @set_metadata(
        connector_def_file_path=DEF_PATH,
        parameters=DEFAULT_PARAMETERS,
        external_context=MockExternalContext(),
        integration_config=CONFIG,
        input_context={"integrationContext": CONFIG}
    )
    def test_connector_test_run_with_messages_no_context(
            self,
            gcloud_pubsub_script_session: ApiSession,
            connector_output: MockConnectorOutput,
            product: Product,
            external_context: MockExternalContext,
    ) -> None:
        product.set_messages(MOCK_DATA["one_test_one_real"])
        set_is_test_run_to_true()
        connector = PubSubMessagesConnector()
        connector.siemplify.context.connector_info.identifier = (
            TEST_CONNECTOR_IDENTIFIER
        )
        connector.start()

        assert len(gcloud_pubsub_script_session.request_history) == 4
        assert_get_subscription(gcloud_pubsub_script_session.request_history, 1)
        assert_pull_messages(gcloud_pubsub_script_session.request_history, 2)
        assert_ack_messages(gcloud_pubsub_script_session.request_history, 3)

        assert len(connector_output.results.json_output.alerts) == 1
        row_key: ExternalContextRowKey = ExternalContextRowKey(
            context_type=DatabaseContextType.CONNECTOR,
            identifier=TEST_CONNECTOR_IDENTIFIER,
            property_key=IDS_DB_KEY,
        )
        assert row_key not in external_context

    @set_metadata(
            connector_def_file_path=DEF_PATH,
            parameters=DEFAULT_PARAMETERS,
            external_context=MockExternalContext(),
            integration_config=CONFIG,
            input_context={"integrationContext": CONFIG}
    )
    def test_connector_run_with_messages_ids(
            self,
            gcloud_pubsub_script_session: ApiSession,
            connector_output: MockConnectorOutput,
            product: Product,
            external_context: MockExternalContext,
    ) -> None:
        product.set_messages(MOCK_DATA["one_test_one_real"])
        set_is_test_run_to_false()
        connector = PubSubMessagesConnector()
        connector.siemplify.context.connector_info.identifier = (
            TEST_CONNECTOR_IDENTIFIER
        )
        connector.start()

        assert len(gcloud_pubsub_script_session.request_history) == 5
        assert_get_subscription(gcloud_pubsub_script_session.request_history, 1)
        assert_pull_messages(gcloud_pubsub_script_session.request_history, 2)
        assert_ack_messages(gcloud_pubsub_script_session.request_history, 3)
        assert_ack_messages(gcloud_pubsub_script_session.request_history, 4)

        assert len(connector_output.results.json_output.alerts) == 1
        assert all(
            "notificationConfigs" in alert.name
            for alert in connector_output.results.json_output.alerts
        )
        assert all(
            bool(alert.rule_generator)
            for alert in connector_output.results.json_output.alerts
        )
        ids_json = external_context.get_row_value(
            context_type=DatabaseContextType.CONNECTOR,
            identifier=TEST_CONNECTOR_IDENTIFIER,
            property_key=IDS_DB_KEY,
        )
        assert ids_json

        ids: list[str] = json.loads(ids_json)
        assert len(ids) == 1


    @set_metadata(
            connector_def_file_path=DEF_PATH,
            parameters=DEFAULT_PARAMETERS,
            external_context=MockExternalContext(),
            integration_config=CONFIG,
            input_context={"integrationContext": CONFIG}
    )
    def test_connector_run_with_messages_ids_and_non_json(
            self,
            gcloud_pubsub_script_session: ApiSession,
            connector_output: MockConnectorOutput,
            product: Product,
            external_context: MockExternalContext,
    ) -> None:
        product.set_messages(MOCK_DATA["two_real_one_broken"])
        set_is_test_run_to_false()
        connector = PubSubMessagesConnector()
        connector.siemplify.context.connector_info.identifier = (
            TEST_CONNECTOR_IDENTIFIER
        )
        connector.start()

        assert len(gcloud_pubsub_script_session.request_history) == 4
        assert_get_subscription(gcloud_pubsub_script_session.request_history, 1)
        assert_pull_messages(gcloud_pubsub_script_session.request_history, 2)
        assert_ack_messages(gcloud_pubsub_script_session.request_history, 3)

        assert len(connector_output.results.json_output.alerts) == 3
        ids_json = external_context.get_row_value(
            context_type=DatabaseContextType.CONNECTOR,
            identifier=TEST_CONNECTOR_IDENTIFIER,
            property_key=IDS_DB_KEY,
        )
        assert ids_json

        ids: list[str] = json.loads(ids_json)
        assert len(ids) == 3
