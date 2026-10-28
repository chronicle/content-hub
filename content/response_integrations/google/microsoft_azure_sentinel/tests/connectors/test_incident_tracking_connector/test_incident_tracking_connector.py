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

import sys
import os
import pathlib
import unittest
from unittest.mock import Mock, patch, AsyncMock, PropertyMock
import asyncio
import httpx
import datetime

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
)

from microsoft_azure_sentinel.connectors.IncidentTrackingConnector import (
    IncidentTrackingConnector,
)
from microsoft_azure_sentinel.core.MicrosoftAzureSentinelAsyncManager import (
    MicrosoftAzureSentinelAsyncManager,
)
from microsoft_azure_sentinel.core.datamodels import Incident

from integration_testing.set_meta import set_metadata
from integration_testing.common import set_is_test_run_to_true, set_is_test_run_to_false

DEF_PATH = (
    pathlib.Path(__file__).resolve().parents[3]
    / "connectors"
    / "IncidentTrackingConnector.yaml"
)

DEFAULT_PARAMETERS = {
    "API Root": "https://management.azure.com",
    "Client ID": "test-client-id",
    "Client Secret": "test-client-secret",
    "Azure Active Directory ID": "test-tenant-id",
    "Azure Sentinel Workspace Name": "test-workspace",
    "Azure Resource Group": "test-rg",
    "Azure Subscription ID": "test-sub-id",
    "Verify SSL": True,
    "Use dynamic list as a blocklist": False,
    "Max incidents per cycle": 5,
    "Alerts for no entities": False,
    "Use same approach": True,
    "Wait for scheduled alerts": False,
}


class TestIncidentTrackingConnector(unittest.TestCase):

    def setUp(self):
        set_is_test_run_to_true()
        self.is_test = True

    @set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
    @patch("httpx.AsyncClient")
    def test_429_retry(self, mock_client_class):
        """Verify that 429 responses trigger retry logic."""

        async def run_test():
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            resp429 = Mock(spec=httpx.Response)
            resp429.status_code = 429
            resp429.headers = {"Retry-After": "5"}
            resp429.text = "Too Many Requests"

            resp200 = Mock(spec=httpx.Response)
            resp200.status_code = 200
            resp200.json.return_value = {"value": []}

            mock_client.get = AsyncMock(side_effect=[resp429, resp200])

            with patch.object(
                MicrosoftAzureSentinelAsyncManager,
                "fetch_token",
                return_value="dummy_token",
            ):
                manager = MicrosoftAzureSentinelAsyncManager(
                    http_timeout_seconds=60,
                    api_root=DEFAULT_PARAMETERS["API Root"],
                    login_url="https://login.microsoftonline.com",
                    client_id=DEFAULT_PARAMETERS["Client ID"],
                    client_secret=DEFAULT_PARAMETERS["Client Secret"],
                    tenant_id=DEFAULT_PARAMETERS["Azure Active Directory ID"],
                    workspace_id=DEFAULT_PARAMETERS["Azure Sentinel Workspace Name"],
                    resource=DEFAULT_PARAMETERS["Azure Resource Group"],
                    subscription_id=DEFAULT_PARAMETERS["Azure Subscription ID"],
                )
            manager.async_client = mock_client
            manager.logger = Mock()

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                response = await manager._execute_async_request_with_retry(
                    mock_client.get, "http://test"
                )

                self.assertEqual(response.status_code, 200)
                mock_sleep.assert_awaited_once_with(7)

        asyncio.run(run_test())

    @set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
    @patch("httpx.AsyncClient")
    def test_get_incident_entities_raises_cancelled(self, mock_client_class):
        """Verify that CancelledError is re-raised."""

        async def run_test():
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.post = AsyncMock(side_effect=asyncio.CancelledError())

            with patch.object(
                MicrosoftAzureSentinelAsyncManager,
                "fetch_token",
                return_value="dummy_token",
            ):
                manager = MicrosoftAzureSentinelAsyncManager(
                    http_timeout_seconds=60,
                    api_root=DEFAULT_PARAMETERS["API Root"],
                    login_url="https://login.microsoftonline.com",
                    client_id=DEFAULT_PARAMETERS["Client ID"],
                    client_secret=DEFAULT_PARAMETERS["Client Secret"],
                    tenant_id=DEFAULT_PARAMETERS["Azure Active Directory ID"],
                    workspace_id=DEFAULT_PARAMETERS["Azure Sentinel Workspace Name"],
                    resource=DEFAULT_PARAMETERS["Azure Resource Group"],
                    subscription_id=DEFAULT_PARAMETERS["Azure Subscription ID"],
                )
            manager.async_client = mock_client
            manager.logger = Mock()

            with self.assertRaises(asyncio.CancelledError):
                await manager.get_incident_entities("alert_id", 1, "incident_id", {})

        asyncio.run(run_test())

    @set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
    @patch(
        "microsoft_azure_sentinel.connectors.IncidentTrackingConnector.filter_old_alerts"
    )
    def test_filter_ordering(self, mock_filter_old_alerts):
        """Verify that filters are applied correctly in filter_alerts."""
        with patch.object(
            IncidentTrackingConnector, "siemplify", new_callable=PropertyMock
        ) as mock_siemplify, patch.object(
            IncidentTrackingConnector, "logger", new_callable=PropertyMock
        ) as mock_logger, patch.object(
            IncidentTrackingConnector, "context", new_callable=PropertyMock
        ) as mock_context, patch.object(
            IncidentTrackingConnector, "connector_start_time", new_callable=PropertyMock
        ) as mock_start_time:

            mock_siemplify.return_value = Mock()
            mock_logger.return_value = Mock()
            mock_start_time.return_value = 0

            mock_context_instance = Mock()
            mock_context_instance.expired_existing_ids = []
            mock_context_instance.backlog_ids = {}
            mock_context_instance.existing_ids = {}
            mock_context.return_value = mock_context_instance

            connector = IncidentTrackingConnector()

            alert1 = Mock(spec=Incident)
            alert1.name = "alert1"
            alert1.last_modified_time_ts = 1000
            alert1.is_from_backlog = True
            alert1.properties = Mock()
            alert1.properties.incident_number = 1

            alert2 = Mock(spec=Incident)
            alert2.name = "alert2"
            alert2.last_modified_time_ts = 2000
            alert2.is_from_backlog = True
            alert2.properties = Mock()
            alert2.properties.incident_number = 2

            alerts = [alert1, alert2]

            connector._pass_dynamic_list_filter_and_adjust_backlog = Mock(
                return_value=True
            )
            connector._pass_tags_filter_and_adjust_backlog = Mock(
                side_effect=lambda a, n: a.name == "alert1"
            )

            mock_filter_old_alerts.side_effect = (
                lambda siemplify, alerts, existing_ids, id_key: alerts
            )

            filtered_alerts = connector.filter_alerts(alerts)

            self.assertEqual(len(filtered_alerts), 1)
            self.assertEqual(filtered_alerts[0].name, "alert1")

            self.assertEqual(
                connector._pass_dynamic_list_filter_and_adjust_backlog.call_count, 2
            )
            self.assertEqual(
                connector._pass_tags_filter_and_adjust_backlog.call_count, 2
            )

    @set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
    def test_batching_behavior(self):
        """Verify that adjust_incidents_alerts_data processes alerts in batches of 5."""

        async def run_test():
            with patch.object(
                MicrosoftAzureSentinelAsyncManager,
                "fetch_token",
                return_value="dummy_token",
            ):
                manager = MicrosoftAzureSentinelAsyncManager(
                    http_timeout_seconds=60,
                    api_root=DEFAULT_PARAMETERS["API Root"],
                    login_url="https://login.microsoftonline.com",
                    client_id=DEFAULT_PARAMETERS["Client ID"],
                    client_secret=DEFAULT_PARAMETERS["Client Secret"],
                    tenant_id=DEFAULT_PARAMETERS["Azure Active Directory ID"],
                    workspace_id=DEFAULT_PARAMETERS["Azure Sentinel Workspace Name"],
                    resource=DEFAULT_PARAMETERS["Azure Resource Group"],
                    subscription_id=DEFAULT_PARAMETERS["Azure Subscription ID"],
                )
            manager.logger = Mock()

            incident = Mock(spec=Incident)
            incident.name = "incident1"
            incident.properties = Mock()
            incident.properties.incident_number = 1
            incident.properties.alerts = []

            mock_alerts = []
            for i in range(6):
                alert = Mock()
                alert.fully_fetched = False
                mock_alerts.append(alert)

            manager.get_incident_alerts_by_id = AsyncMock(return_value=mock_alerts)
            manager.set_entities_data = Mock(return_value=None)

            with patch("asyncio.gather", new_callable=AsyncMock) as mock_gather, patch(
                "microsoft_azure_sentinel.core.MicrosoftAzureSentinelAsyncManager.MicrosoftAzureSentinelCommon.raise_if_timeout",
                return_value=None,
            ):
                mock_gather.side_effect = [[None] * 5, [None] * 1]

                await manager.adjust_incidents_alerts_data(
                    incident=incident,
                    connector_starting_time=0,
                    python_process_timeout=60,
                    incidents_alerts_limit_to_ingest=10,
                    use_same_approach=True,
                    scheduled_alerts_events_limit=10,
                    backlog_ids={},
                    alerts_for_no_entities=False,
                    wait_for_scheduled_alerts=False,
                )

                self.assertEqual(mock_gather.call_count, 2)
                args_call1 = mock_gather.call_args_list[0].args
                self.assertEqual(len(args_call1), 5)
                args_call2 = mock_gather.call_args_list[1].args
                self.assertEqual(len(args_call2), 1)

        asyncio.run(run_test())

    @set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
    def test_fault_tolerance_in_gather(self):
        """Verify that exceptions in gather do not crash the batch and mark incident correctly."""

        async def run_test():
            with patch.object(
                MicrosoftAzureSentinelAsyncManager,
                "fetch_token",
                return_value="dummy_token",
            ):
                manager = MicrosoftAzureSentinelAsyncManager(
                    http_timeout_seconds=60,
                    api_root=DEFAULT_PARAMETERS["API Root"],
                    login_url="https://login.microsoftonline.com",
                    client_id=DEFAULT_PARAMETERS["Client ID"],
                    client_secret=DEFAULT_PARAMETERS["Client Secret"],
                    tenant_id=DEFAULT_PARAMETERS["Azure Active Directory ID"],
                    workspace_id=DEFAULT_PARAMETERS["Azure Sentinel Workspace Name"],
                    resource=DEFAULT_PARAMETERS["Azure Resource Group"],
                    subscription_id=DEFAULT_PARAMETERS["Azure Subscription ID"],
                )
            manager.logger = Mock()

            incident = Mock(spec=Incident)
            incident.name = "incident1"
            incident.properties = Mock()
            incident.properties.incident_number = 1
            incident.properties.alerts = []

            alert1 = Mock()
            alert1.fully_fetched = False
            alert1.is_scheduled_or_nrt.return_value = False

            alert2 = Mock()
            alert2.fully_fetched = False
            alert2.is_scheduled_or_nrt.return_value = False

            mock_alerts = [alert1, alert2]
            manager.get_incident_alerts_by_id = AsyncMock(return_value=mock_alerts)

            async def mock_set_entities(alert, *args, **kwargs):
                if alert == alert1:
                    raise Exception("Test error")
                alert.fully_fetched = True
                return None

            manager.set_entities_data = Mock(side_effect=mock_set_entities)

            with patch(
                "microsoft_azure_sentinel.core.MicrosoftAzureSentinelAsyncManager.MicrosoftAzureSentinelCommon.raise_if_timeout",
                return_value=None,
            ):
                await manager.adjust_incidents_alerts_data(
                    incident=incident,
                    connector_starting_time=0,
                    python_process_timeout=60,
                    incidents_alerts_limit_to_ingest=10,
                    use_same_approach=True,
                    scheduled_alerts_events_limit=10,
                    backlog_ids={},
                    alerts_for_no_entities=False,
                    wait_for_scheduled_alerts=False,
                )

            manager.logger.error.assert_called()
            self.assertTrue(alert2.fully_fetched)
            self.assertFalse(alert1.fully_fetched)
            self.assertFalse(incident.fully_fetched)

        asyncio.run(run_test())

    @set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
    def test_backlog_loop_resilience(self):
        """Verify that an error fetching one backlog incident doesn't crash the loop."""

        async def run_test():
            with patch.object(
                IncidentTrackingConnector, "siemplify", new_callable=PropertyMock
            ) as mock_siemplify, patch.object(
                IncidentTrackingConnector, "logger", new_callable=PropertyMock
            ) as mock_logger, patch.object(
                IncidentTrackingConnector, "context", new_callable=PropertyMock
            ) as mock_context:

                mock_siemplify.return_value = Mock()
                mock_logger.return_value = Mock()

                mock_context_instance = Mock()
                mock_context_instance.backlog_ids = ["1", "2"]
                mock_context.return_value = mock_context_instance

                connector = IncidentTrackingConnector()
                connector.manager = Mock()
                connector.manager.get_incident_alerts_by_id = AsyncMock(return_value=[])

                async def mock_get_incident(incident_number):
                    if incident_number == "1":
                        raise Exception("Test error")
                    mock_incident = Mock(spec=Incident)
                    mock_incident.name = "incident2"
                    mock_incident.properties = Mock()
                    mock_incident.properties.incident_number = 2
                    mock_incident.properties.alerts = []
                    return mock_incident

                connector.manager.get_incident_by_number = Mock(
                    side_effect=mock_get_incident
                )

                with patch.object(
                    IncidentTrackingConnector, "params", new_callable=PropertyMock
                ) as mock_params, patch.object(
                    IncidentTrackingConnector,
                    "connector_start_time",
                    new_callable=PropertyMock,
                ) as mock_start_time:

                    mock_params_instance = Mock()
                    mock_params.return_value = mock_params_instance
                    mock_params_instance.max_backlog_incidents_per_cycle = 10
                    mock_params_instance.python_process_timeout = 60

                    mock_start_time.return_value = 0

                    connector.sentinel_common = Mock()

                    results = await connector._get_backlog_incidents()

                connector.logger.error.assert_called()
                self.assertEqual(len(results), 1)
                self.assertEqual(results[0].name, "incident2")

        asyncio.run(run_test())

    @set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
    def test_case_insensitive_tag_matching(self):
        """Verify that tag matching is case-insensitive."""
        with patch.object(
            IncidentTrackingConnector, "siemplify", new_callable=PropertyMock
        ) as mock_siemplify, patch.object(
            IncidentTrackingConnector, "logger", new_callable=PropertyMock
        ) as mock_logger, patch.object(
            IncidentTrackingConnector, "context", new_callable=PropertyMock
        ) as mock_context:

            mock_siemplify.return_value = Mock()
            mock_logger.return_value = Mock()

            mock_context_instance = Mock()
            mock_context_instance.backlog_ids = {}
            mock_context.return_value = mock_context_instance

            connector = IncidentTrackingConnector()
            connector.params.incidents_tags_to_ingest = ["tag1", "TAG2"]

            alert = Mock(spec=Incident)
            alert.name = "alert1"
            alert.incident_labels = ["TAG1", "tag2"]

            result = connector._pass_tags_filter_and_adjust_backlog(alert, "1")
            self.assertTrue(result)

            alert2 = Mock(spec=Incident)
            alert2.name = "alert2"
            alert2.incident_labels = ["tag3"]

            result2 = connector._pass_tags_filter_and_adjust_backlog(alert2, "2")
            self.assertFalse(result2)

    @set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
    def test_tags_filter_any_match(self):
        """Verify that tag filtering passes if ANY tag matches."""
        with patch.object(
            IncidentTrackingConnector, "siemplify", new_callable=PropertyMock
        ) as mock_siemplify, patch.object(
            IncidentTrackingConnector, "logger", new_callable=PropertyMock
        ) as mock_logger, patch.object(
            IncidentTrackingConnector, "context", new_callable=PropertyMock
        ) as mock_context:

            mock_siemplify.return_value = Mock()
            mock_logger.return_value = Mock()

            mock_context_instance = Mock()
            mock_context_instance.backlog_ids = {}
            mock_context.return_value = mock_context_instance

            connector = IncidentTrackingConnector()
            connector.params.incidents_tags_to_ingest = [
                "secops tag",
                "secops test tag",
            ]

            alert = Mock(spec=Incident)
            alert.name = "alert1"
            alert.incident_labels = ["Google SecOps: test tag", "secops tag"]

            result = connector._pass_tags_filter_and_adjust_backlog(alert, "1")
            self.assertTrue(result)

            alert2 = Mock(spec=Incident)
            alert2.name = "alert2"
            alert2.incident_labels = ["redirected", "another tag"]

            result2 = connector._pass_tags_filter_and_adjust_backlog(alert2, "2")
            self.assertFalse(result2)

    @set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
    def test_filter_prioritization(self):
        """Verify that new incidents are prioritized over backlog incidents."""
        with patch.object(
            IncidentTrackingConnector, "siemplify", new_callable=PropertyMock
        ) as mock_siemplify, patch.object(
            IncidentTrackingConnector, "logger", new_callable=PropertyMock
        ) as mock_logger, patch.object(
            IncidentTrackingConnector, "context", new_callable=PropertyMock
        ) as mock_context:

            mock_siemplify.return_value = Mock()
            mock_logger.return_value = Mock()

            mock_context_instance = Mock()
            mock_context_instance.existing_ids = {}
            mock_context.return_value = mock_context_instance

            connector = IncidentTrackingConnector()

            alert1 = Mock(spec=Incident)
            alert1.name = "alert1"
            alert1.last_modified_time_ts = 2000
            alert1.is_from_backlog = True
            alert1.properties = Mock()
            alert1.properties.incident_number = 1

            alert2 = Mock(spec=Incident)
            alert2.name = "alert2"
            alert2.last_modified_time_ts = 1000
            alert2.is_from_backlog = False

            alert3 = Mock(spec=Incident)
            alert3.name = "alert3"
            alert3.last_modified_time_ts = 3000
            alert3.is_from_backlog = False

            alerts = [alert1, alert2, alert3]

            connector._pass_dynamic_list_filter_and_adjust_backlog = Mock(
                return_value=True
            )
            connector._pass_tags_filter_and_adjust_backlog = Mock(return_value=True)

            filtered_alerts = connector.filter_alerts(alerts)

            self.assertEqual(len(filtered_alerts), 3)
            self.assertEqual(filtered_alerts[0].name, "alert2")
            self.assertEqual(filtered_alerts[1].name, "alert3")
            self.assertEqual(filtered_alerts[2].name, "alert1")

    @set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
    def test_get_alerts_preserves_next_page_link(self):
        """Verify next_page_link contains the new link from the last fetch."""

        async def run_test():
            with patch.object(
                IncidentTrackingConnector, "siemplify", new_callable=PropertyMock
            ) as mock_siemplify, patch.object(
                IncidentTrackingConnector, "logger", new_callable=PropertyMock
            ) as mock_logger, patch.object(
                IncidentTrackingConnector, "context", new_callable=PropertyMock
            ) as mock_context, patch.object(
                IncidentTrackingConnector,
                "connector_start_time",
                new_callable=PropertyMock,
            ) as mock_start_time, patch.object(
                IncidentTrackingConnector, "params", new_callable=PropertyMock
            ) as mock_params:

                mock_siemplify_instance = Mock()
                mock_siemplify_instance.whitelist = []
                mock_siemplify.return_value = mock_siemplify_instance

                mock_logger.return_value = Mock()
                mock_start_time.return_value = 123456

                mock_params_instance = Mock()
                mock_params.return_value = mock_params_instance
                mock_params_instance.max_incidents_per_cycle = 2
                mock_params_instance.use_dynamic_list_as_a_blocklist = False
                mock_params_instance.incidents_tags_to_ingest = []
                mock_params_instance.incident_creation_time_filter_days = None
                mock_params_instance.incident_statuses_to_fetch = []
                mock_params_instance.incident_severities_to_fetch = []

                mock_context_instance = Mock()
                mock_context_instance.existing_ids = {}
                mock_context_instance.expired_existing_ids = []
                mock_context_instance.last_success_timestamp = datetime.datetime(
                    2026, 4, 15, 11, 0, 0, tzinfo=datetime.timezone.utc
                )
                mock_context_instance.next_page_link = "initial_link"
                mock_context_instance.existing_ids_changed = False
                mock_context.return_value = mock_context_instance

                connector = IncidentTrackingConnector()
                connector.manager = mock_manager = Mock()

                alerts = []
                for i in range(5):
                    alert = Mock(spec=Incident)
                    alert.name = f"alert_{i}"
                    alert.incident_labels = []
                    alert.properties = Mock()
                    alert.properties.incident_number = i
                    alert.properties.last_modified_time_utc = "2026-04-15T12:00:00Z"
                    alert.properties.alerts = []
                    alert.raw_to_flat_data = Mock(return_value={})
                    alerts.append(alert)

                from unittest.mock import AsyncMock

                mock_get_incidents = AsyncMock(return_value=(alerts, "new_link"))
                mock_manager.get_incidents_with_new_endpoint = mock_get_incidents

                connector._get_backlog_incidents = AsyncMock(return_value=[])
                connector._fetch_events_if_needed = AsyncMock()

                valid_alerts = await connector.get_alerts()

                self.assertEqual(len(valid_alerts), 2)

                self.assertEqual(mock_context_instance.next_page_link, "new_link")

        asyncio.run(run_test())

    @set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
    @patch("httpx.AsyncClient")
    def test_server_error_retry(self, mock_client_class):
        """Verify that 502/503/504 responses trigger retry logic in manager."""

        async def run_test():
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            resp502 = Mock(spec=httpx.Response)
            resp502.status_code = 502

            resp200 = Mock(spec=httpx.Response)
            resp200.status_code = 200
            resp200.json.return_value = {"value": []}

            mock_client.get = AsyncMock(side_effect=[resp502, resp200])

            with patch.object(
                MicrosoftAzureSentinelAsyncManager,
                "fetch_token",
                return_value="dummy_token",
            ):
                manager = MicrosoftAzureSentinelAsyncManager(
                    http_timeout_seconds=60,
                    api_root=DEFAULT_PARAMETERS["API Root"],
                    login_url="https://login.microsoftonline.com",
                    client_id=DEFAULT_PARAMETERS["Client ID"],
                    client_secret=DEFAULT_PARAMETERS["Client Secret"],
                    tenant_id=DEFAULT_PARAMETERS["Azure Active Directory ID"],
                    workspace_id=DEFAULT_PARAMETERS["Azure Sentinel Workspace Name"],
                    resource=DEFAULT_PARAMETERS["Azure Resource Group"],
                    subscription_id=DEFAULT_PARAMETERS["Azure Subscription ID"],
                )
            manager.async_client = mock_client
            manager.logger = Mock()

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                response = await manager._execute_async_request_with_retry(
                    mock_client.get, "http://test"
                )

                self.assertEqual(response.status_code, 200)
                mock_sleep.assert_awaited_once_with(5)

        asyncio.run(run_test())

    @set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
    @patch(
        "microsoft_azure_sentinel.connectors.IncidentTrackingConnector.create_regular_alert_events"
    )
    def test_slice_events_into_alerts(self, mock_create_regular_events):
        """Verify that incidents with more events than chunk size are split into separate alerts."""
        with patch.object(
            IncidentTrackingConnector, "siemplify", new_callable=PropertyMock
        ) as mock_siemplify, patch.object(
            IncidentTrackingConnector, "logger", new_callable=PropertyMock
        ) as mock_logger, patch.object(
            IncidentTrackingConnector, "params", new_callable=PropertyMock
        ) as mock_params:

            mock_siemplify.return_value = Mock()
            mock_logger.return_value = Mock()

            mock_params_instance = Mock()
            mock_params.return_value = mock_params_instance
            mock_params_instance.create_extra_events_for_all_entities = False
            mock_params_instance.product_field_fallback = []
            mock_params_instance.fallback_logic_debug = False
            mock_params_instance.use_same_approach = True

            connector = IncidentTrackingConnector()

            alert = Mock(spec=Incident)
            alert.name = "big_incident"
            alert.raw_to_flat_data = Mock(
                return_value={"incident_title": "Test big incident"}
            )
            alert.properties = Mock()
            alert.properties.incident_number = 999
            alert.properties.additional_data = None
            alert.is_from_backlog = False

            mock_incident_alert = Mock()
            mock_incident_alert.name = "sentinel_alert"
            mock_incident_alert.properties = Mock()
            mock_incident_alert.properties.start_time_utc = "2026-04-15T12:00:00Z"
            mock_incident_alert.is_scheduled_or_nrt.return_value = False
            mock_incident_alert.to_event.return_value = {"event_field": "val"}

            alert.properties.alerts = [mock_incident_alert]

            mock_create_regular_events.return_value = [
                {"event_num": i} for i in range(150)
            ]

            sliced_alerts = connector._slice_events_into_alerts([alert])

            self.assertEqual(len(sliced_alerts), 2)

            # Check first slice
            self.assertEqual(sliced_alerts[0].name, "big_incident_0")
            self.assertEqual(sliced_alerts[0].original_name, "big_incident")
            self.assertEqual(len(sliced_alerts[0].events_slice), 100)

            # Check second slice
            self.assertEqual(sliced_alerts[1].name, "big_incident_1")
            self.assertEqual(sliced_alerts[1].original_name, "big_incident")
            self.assertEqual(len(sliced_alerts[1].events_slice), 51)

    @set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
    def test_get_alerts_creation_time_filtering(self):
        """Verify that creation_time parameter filter is correctly calculated and passed."""

        async def run_test():
            with patch.object(
                IncidentTrackingConnector, "siemplify", new_callable=PropertyMock
            ) as mock_siemplify, patch.object(
                IncidentTrackingConnector, "logger", new_callable=PropertyMock
            ) as mock_logger, patch.object(
                IncidentTrackingConnector, "context", new_callable=PropertyMock
            ) as mock_context, patch.object(
                IncidentTrackingConnector,
                "connector_start_time",
                new_callable=PropertyMock,
            ) as mock_start_time, patch.object(
                IncidentTrackingConnector, "params", new_callable=PropertyMock
            ) as mock_params:

                mock_siemplify_instance = Mock()
                mock_siemplify_instance.whitelist = []
                mock_siemplify.return_value = mock_siemplify_instance

                mock_logger.return_value = Mock()
                mock_start_time.return_value = 123456

                mock_params_instance = Mock()
                mock_params.return_value = mock_params_instance
                mock_params_instance.max_incidents_per_cycle = 5
                mock_params_instance.use_dynamic_list_as_a_blocklist = False
                mock_params_instance.incidents_tags_to_ingest = []
                mock_params_instance.incident_creation_time_filter_days = 3
                mock_params_instance.incident_statuses_to_fetch = []
                mock_params_instance.incident_severities_to_fetch = []

                mock_context_instance = Mock()
                mock_context_instance.existing_ids = {}
                mock_context_instance.expired_existing_ids = []
                mock_context_instance.last_success_timestamp = datetime.datetime(
                    2026, 4, 15, 11, 0, 0, tzinfo=datetime.timezone.utc
                )
                mock_context_instance.next_page_link = ""
                mock_context_instance.existing_ids_changed = False
                mock_context.return_value = mock_context_instance

                connector = IncidentTrackingConnector()
                connector.manager = mock_manager = Mock()

                from unittest.mock import AsyncMock

                mock_get_incidents = AsyncMock(return_value=([], ""))
                mock_manager.get_incidents_with_new_endpoint = mock_get_incidents

                connector._get_backlog_incidents = AsyncMock(return_value=[])

                static_utc_now = datetime.datetime(
                    2026, 5, 27, 20, 0, 0, tzinfo=datetime.timezone.utc
                )
                with patch(
                    "microsoft_azure_sentinel.connectors.IncidentTrackingConnector.utc_now",
                    return_value=static_utc_now,
                ):
                    await connector.get_alerts()

                mock_get_incidents.assert_called_once()
                call_kwargs = mock_get_incidents.call_args[1]

                expected_creation_time = static_utc_now - datetime.timedelta(days=3)
                self.assertEqual(call_kwargs["creation_time"], expected_creation_time)

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
