from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import requests

from core import DoppelManager as dm_module
from core.DoppelManager import DEFAULT_TIMEOUT_SECONDS, DoppelManager

API_KEY = "test-api-key"
USER_API_KEY = "test-user-api-key"
ORG_CODE = "test-org"


def build_response(payload=None, error=None):
    """Builds a mock requests.Response returning payload, or raising on status."""
    response = MagicMock()
    response.json.return_value = payload if payload is not None else {}
    if error is None:
        response.raise_for_status.return_value = None
    else:
        response.raise_for_status.side_effect = error
    return response


class TestDoppelManagerHeaders(unittest.TestCase):
    def test_headers_omit_absent_optional_credentials(self):
        manager = DoppelManager(api_key=API_KEY, user_api_key=None, org_code=None)

        headers = manager._get_headers()

        self.assertEqual(headers["x-api-key"], API_KEY)
        self.assertNotIn("x-user-api-key", headers)
        self.assertNotIn("x-organization-code", headers)

    def test_headers_include_optional_credentials_when_set(self):
        manager = DoppelManager(
            api_key=API_KEY,
            user_api_key=USER_API_KEY,
            org_code=ORG_CODE,
        )

        headers = manager._get_headers()

        self.assertEqual(headers["x-user-api-key"], USER_API_KEY)
        self.assertEqual(headers["x-organization-code"], ORG_CODE)


class TestDoppelManagerIdentifierValidation(unittest.TestCase):
    def setUp(self):
        self.manager = DoppelManager(api_key=API_KEY, user_api_key=None, org_code=None)

    def test_get_alert_rejects_both_identifiers(self):
        with self.assertRaises(ValueError):
            self.manager.get_alert(entity="https://example.com", alert_id="TST-1")

    def test_get_alert_rejects_missing_identifier(self):
        with self.assertRaises(ValueError):
            self.manager.get_alert()

    def test_update_alert_rejects_both_identifiers(self):
        with self.assertRaises(ValueError):
            self.manager.update_alert(
                queue_state="actioned",
                entity_state="down",
                entity="https://example.com",
                alert_id="TST-1",
            )

    def test_update_alert_rejects_missing_identifier(self):
        with self.assertRaises(ValueError):
            self.manager.update_alert(queue_state="actioned", entity_state="down")


class TestDoppelManagerRequests(unittest.TestCase):
    def setUp(self):
        self.manager = DoppelManager(api_key=API_KEY, user_api_key=None, org_code=None)

    @patch.object(dm_module.requests, "request")
    def test_get_alert_by_entity_queries_entity_param(self, mock_request):
        mock_request.return_value = build_response({"id": "TST-1"})

        result = self.manager.get_alert(entity="https://example.com")

        self.assertEqual(result, {"id": "TST-1"})
        _, kwargs = mock_request.call_args
        self.assertEqual(kwargs["params"], {"entity": "https://example.com"})

    @patch.object(dm_module.requests, "request")
    def test_get_alert_by_id_queries_id_param(self, mock_request):
        mock_request.return_value = build_response({"id": "TST-1"})

        self.manager.get_alert(alert_id="TST-1")

        _, kwargs = mock_request.call_args
        self.assertEqual(kwargs["params"], {"id": "TST-1"})

    @patch.object(dm_module.requests, "request")
    def test_every_request_sends_a_timeout(self, mock_request):
        mock_request.return_value = build_response({"alerts": []})

        self.manager.get_alerts()

        _, kwargs = mock_request.call_args
        self.assertEqual(kwargs["timeout"], DEFAULT_TIMEOUT_SECONDS)

    @patch.object(dm_module.requests, "request")
    def test_get_alerts_returns_empty_list_when_nothing_matches(self, mock_request):
        mock_request.return_value = build_response({"alerts": []})

        self.assertEqual(self.manager.get_alerts(), [])

    @patch.object(dm_module.requests, "request")
    def test_get_alerts_returns_empty_list_when_key_absent(self, mock_request):
        mock_request.return_value = build_response({})

        self.assertEqual(self.manager.get_alerts(), [])

    @patch.object(dm_module.requests, "request")
    def test_update_alert_sends_states_in_body(self, mock_request):
        mock_request.return_value = build_response({"id": "TST-1"})

        self.manager.update_alert(
            queue_state="actioned",
            entity_state="down",
            alert_id="TST-1",
        )

        _, kwargs = mock_request.call_args
        self.assertEqual(
            kwargs["json"],
            {"queue_state": "actioned", "entity_state": "down"},
        )


class TestDoppelManagerErrorPropagation(unittest.TestCase):
    """API failures must reach the caller so actions can report the real cause."""

    def setUp(self):
        self.manager = DoppelManager(api_key=API_KEY, user_api_key=None, org_code=None)

    @patch.object(dm_module.requests, "request")
    def test_get_alerts_propagates_http_error(self, mock_request):
        mock_request.return_value = build_response(
            error=requests.HTTPError("401 Client Error: Unauthorized"),
        )

        with self.assertRaises(requests.HTTPError):
            self.manager.get_alerts()

    @patch.object(dm_module.requests, "request")
    def test_create_alert_propagates_connection_error(self, mock_request):
        mock_request.side_effect = requests.ConnectionError("connection refused")

        with self.assertRaises(requests.ConnectionError):
            self.manager.create_alert(entity="https://example.com")

    @patch.object(dm_module.requests, "request")
    def test_update_alert_propagates_timeout(self, mock_request):
        mock_request.side_effect = requests.Timeout("timed out")

        with self.assertRaises(requests.Timeout):
            self.manager.update_alert(
                queue_state="actioned",
                entity_state="down",
                alert_id="TST-1",
            )


class TestDoppelManagerConnectionTest(unittest.TestCase):
    """connection_test keeps its boolean contract for the Ping action."""

    def setUp(self):
        self.manager = DoppelManager(api_key=API_KEY, user_api_key=None, org_code=None)

    @patch.object(dm_module.requests, "request")
    def test_connection_test_true_on_success(self, mock_request):
        mock_request.return_value = build_response({"alerts": []})

        self.assertTrue(self.manager.connection_test())

    @patch.object(dm_module.requests, "request")
    def test_connection_test_false_on_http_error(self, mock_request):
        mock_request.return_value = build_response(
            error=requests.HTTPError("403 Client Error: Forbidden"),
        )

        self.assertFalse(self.manager.connection_test())

    @patch.object(dm_module.requests, "request")
    def test_connection_test_false_on_connection_error(self, mock_request):
        mock_request.side_effect = requests.ConnectionError("connection refused")

        self.assertFalse(self.manager.connection_test())


if __name__ == "__main__":
    unittest.main()
