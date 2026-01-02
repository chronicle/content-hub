"""Tests for HoudinManager scan and polling functionality."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from requests.exceptions import HTTPError, RequestException

from ..core.houdin import API_ROOT, HoudinManager


class TestHoudinManager:
    """Test class for HoudinManager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.api_key = "test_api_key_12345"
        self.manager = HoudinManager(api_key=self.api_key)
        self.test_artifact = "test.com"
        self.test_scan_id = "scan_12345"

    def test_init(self):
        """Test HoudinManager initialization."""
        manager = HoudinManager(api_key="test_key")
        assert manager.api_key == "test_key"

    def test_clean_scan_on_valid_scanners(self):
        """Test cleanScanOn with valid scanners."""
        input_list = ["vt", "urlscan", "mesmer"]
        result = self.manager.cleanScanOn(input_list)
        assert result == ["vt", "urlscan", "mesmer"]

    def test_clean_scan_on_with_custom_scanner(self):
        """Test cleanScanOn with custom scanner."""
        input_list = ["vt", "custom_scanner_1", "invalid"]
        result = self.manager.cleanScanOn(input_list)
        assert result == ["vt", "custom_scanner_1"]

    def test_clean_scan_on_with_whitespace(self):
        """Test cleanScanOn removes whitespace."""
        input_list = ["  vt  ", " urlscan ", "mesmer"]
        result = self.manager.cleanScanOn(input_list)
        assert result == ["vt", "urlscan", "mesmer"]

    def test_clean_scan_on_invalid_types(self):
        """Test cleanScanOn filters out non-string types."""
        input_list = ["vt", 123, None, "urlscan", []]
        result = self.manager.cleanScanOn(input_list)
        assert result == ["vt", "urlscan"]

    def test_clean_scan_on_empty_list(self):
        """Test cleanScanOn with empty or invalid list."""
        assert self.manager.cleanScanOn([]) is None
        assert self.manager.cleanScanOn(["invalid", "scanner"]) is None
        assert self.manager.cleanScanOn([123, None]) is None

    @patch("requests.post")
    def test_launch_scan_success(self, mock_post):
        """Test successful scan launch."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"scanID": self.test_scan_id, "status": "launched"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        scan_id, status = self.manager.launch_scan(self.test_artifact)

        assert scan_id == self.test_scan_id
        assert status == "launched"

        # Verify the request was made correctly
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["json"] == {"artifact": self.test_artifact}
        assert kwargs["headers"]["X-API-Key"] == self.api_key
        assert kwargs["headers"]["Content-Type"] == "application/json"

    @patch("requests.post")
    def test_launch_scan_with_scan_on(self, mock_post):
        """Test scan launch with scanOn parameter."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"scanID": self.test_scan_id, "status": "launched"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        scan_on = ["vt", "urlscan"]
        scan_id, status = self.manager.launch_scan(self.test_artifact, scan_on)

        assert scan_id == self.test_scan_id
        assert status == "launched"

        # Verify scanOn was included in the request
        args, kwargs = mock_post.call_args
        expected_data = {"artifact": self.test_artifact, "scanOn": ["vt", "urlscan"]}
        assert kwargs["json"] == expected_data

    @patch("requests.post")
    def test_launch_scan_with_empty_scan_on(self, mock_post):
        """Test scan launch with empty scanOn parameter."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"scanID": self.test_scan_id, "status": "launched"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        scan_on = [""]
        scan_id, status = self.manager.launch_scan(self.test_artifact, scan_on)

        # Verify scanOn was not included when empty
        args, kwargs = mock_post.call_args
        assert kwargs["json"] == {"artifact": self.test_artifact}

    @patch("requests.post")
    def test_launch_scan_server_error_retry(self, mock_post):
        """Test scan launch with server error and retry."""
        # First call returns 500, second call succeeds
        mock_response_error = Mock()
        mock_response_error.status_code = 500

        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "scanID": self.test_scan_id,
            "status": "launched",
        }
        mock_response_success.raise_for_status.return_value = None

        mock_post.side_effect = [mock_response_error, mock_response_success]

        scan_id, status = self.manager.launch_scan(self.test_artifact)

        assert scan_id == self.test_scan_id
        assert status == "launched"
        assert mock_post.call_count == 2

    @patch("requests.post")
    def test_launch_scan_no_scan_id_in_response(self, mock_post):
        """Test scan launch when no scanID is returned."""
        # Mock response without scanID
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "error", "message": "Invalid artifact"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        with pytest.raises(Exception, match="No scanID received in response"):
            self.manager.launch_scan(self.test_artifact)

    @patch("requests.post")
    def test_launch_scan_request_exception(self, mock_post):
        """Test scan launch with request exception."""
        mock_post.side_effect = RequestException("Connection error")

        with pytest.raises(Exception, match="Connection error"):
            self.manager.launch_scan(self.test_artifact)

    @patch("requests.post")
    def test_launch_scan_http_error(self, mock_post):
        """Test scan launch with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = HTTPError("400 Bad Request")
        mock_post.return_value = mock_response

        with pytest.raises(Exception, match="400 Bad Request"):
            self.manager.launch_scan(self.test_artifact)

    @patch("requests.get")
    def test_poll_scan_result_success(self, mock_get):
        """Test successful scan result polling."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "scanID": self.test_scan_id,
            "status": "Done",
            "artifact": "test.com",
            "scanResults": {
                "vt": {
                    "result": {
                        "data": {
                            "attributes": {
                                "last_analysis_stats": {
                                    "malicious": 0,
                                    "suspicious": 0,
                                    "undetected": 28,
                                    "harmless": 54,
                                },
                                "reputation": 0,
                            }
                        }
                    }
                },
                "urlscan": {
                    "result": {"results": [{"page": {"domain": "test.com", "status": "200"}}]}
                },
            },
            "scanTime": "2025-08-01T10:00:00Z",
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = self.manager.poll_scan_result(self.test_scan_id)

        assert result["scanID"] == self.test_scan_id
        assert result["status"] == "Done"
        assert "scanResults" in result

        # Verify the request was made correctly
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        expected_url = API_ROOT.format(f"scan/result?scanID={self.test_scan_id}")
        assert args[0] == expected_url
        assert kwargs["headers"]["X-API-Key"] == self.api_key
        assert kwargs["headers"]["Accept"] == "application/json"

    @patch("requests.get")
    @patch("time.sleep")
    def test_poll_scan_result_with_pending_status(self, mock_sleep, mock_get):
        """Test polling with initial pending status (202)."""
        # First call returns 202 (pending), second call returns completed
        mock_response_pending = Mock()
        mock_response_pending.status_code = 202

        mock_response_completed = Mock()
        mock_response_completed.status_code = 200
        mock_response_completed.json.return_value = {
            "scanID": self.test_scan_id,
            "status": "Done",
            "scanResults": {"vt": {"result": {"data": {"attributes": {"reputation": 0}}}}},
        }
        mock_response_completed.raise_for_status.return_value = None

        mock_get.side_effect = [mock_response_pending, mock_response_completed]

        result = self.manager.poll_scan_result(self.test_scan_id)

        assert result["status"] == "Done"
        assert mock_get.call_count == 2
        mock_sleep.assert_called_once_with(3)  # Default retry_interval

    @patch("requests.get")
    @patch("time.sleep")
    def test_poll_scan_result_custom_retry_params(self, mock_sleep, mock_get):
        """Test polling with custom retry parameters."""
        # Mock pending then completed responses
        mock_response_pending = Mock()
        mock_response_pending.status_code = 202

        mock_response_completed = Mock()
        mock_response_completed.status_code = 200
        mock_response_completed.json.return_value = {"scanID": self.test_scan_id, "status": "Done"}
        mock_response_completed.raise_for_status.return_value = None

        mock_get.side_effect = [mock_response_pending, mock_response_completed]

        result = self.manager.poll_scan_result(self.test_scan_id, max_retries=5, retry_interval=2)

        assert result["status"] == "Done"
        mock_sleep.assert_called_once_with(2)  # Custom retry_interval

    @patch("requests.get")
    @patch("time.sleep")
    def test_poll_scan_result_max_retries_exceeded(self, mock_sleep, mock_get):
        """Test polling when max retries are exceeded."""
        # Always return 202 (pending)
        mock_response = Mock()
        mock_response.status_code = 202
        mock_get.return_value = mock_response

        with pytest.raises(Exception, match="Polling for scan result failed after maximum retries"):
            self.manager.poll_scan_result(self.test_scan_id, max_retries=2)

        assert mock_get.call_count == 2
        assert mock_sleep.call_count == 2

    @patch("requests.get")
    def test_poll_scan_result_request_exception(self, mock_get):
        """Test polling with request exception."""
        mock_get.side_effect = RequestException("Network error")

        with pytest.raises(Exception, match="Network error"):
            self.manager.poll_scan_result(self.test_scan_id)

    @patch("requests.get")
    def test_poll_scan_result_http_error(self, mock_get):
        """Test polling with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        with pytest.raises(Exception, match="404 Not Found"):
            self.manager.poll_scan_result(self.test_scan_id)


class TestHoudinManagerIntegration:
    """Integration tests for complete scan workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.api_key = "test_api_key_12345"
        self.manager = HoudinManager(api_key=self.api_key)
        self.test_artifact = "test.com"

    @patch("requests.post")
    @patch("requests.get")
    @patch("time.sleep")
    def test_complete_scan_workflow(self, mock_sleep, mock_get, mock_post):
        """Test complete workflow: launch scan -> poll -> get result."""
        # Mock launch scan response
        mock_launch_response = Mock()
        mock_launch_response.status_code = 200
        mock_launch_response.json.return_value = {"scanID": "scan_12345", "status": "launched"}
        mock_launch_response.raise_for_status.return_value = None
        mock_post.return_value = mock_launch_response

        # Mock polling responses: first pending, then completed
        mock_pending_response = Mock()
        mock_pending_response.status_code = 202

        mock_completed_response = Mock()
        mock_completed_response.status_code = 200
        mock_completed_response.json.return_value = {
            "scanID": "scan_12345",
            "status": "Done",
            "artifact": "test.com",
            "scanOn": ["vt", "urlscan"],
            "scanResults": {
                "vt": {
                    "result": {
                        "data": {
                            "attributes": {
                                "last_analysis_stats": {
                                    "malicious": 0,
                                    "suspicious": 0,
                                    "undetected": 28,
                                    "harmless": 54,
                                },
                                "reputation": 0,
                                "registrar": "Reserved Domain",
                            }
                        }
                    }
                },
                "urlscan": {
                    "result": {
                        "results": [
                            {"page": {"domain": "test.com", "status": "200", "country": "US"}}
                        ]
                    }
                },
            },
            "scanTime": "2025-08-01T10:00:00Z",
        }
        mock_completed_response.raise_for_status.return_value = None

        mock_get.side_effect = [mock_pending_response, mock_completed_response]

        # Execute complete workflow
        scan_id, launch_status = self.manager.launch_scan(self.test_artifact, ["vt", "urlscan"])

        assert scan_id == "scan_12345"
        assert launch_status == "launched"

        # Poll for result
        result = self.manager.poll_scan_result(scan_id)

        assert result["status"] == "Done"
        assert result["scanID"] == "scan_12345"
        assert "scanResults" in result
        assert (
            result["scanResults"]["vt"]["result"]["data"]["attributes"]["last_analysis_stats"][
                "malicious"
            ]
            == 0
        )
        assert (
            result["scanResults"]["urlscan"]["result"]["results"][0]["page"]["domain"] == "test.com"
        )
        assert result["artifact"] == "test.com"

        # Verify all requests were made correctly
        assert mock_post.call_count == 1
        assert mock_get.call_count == 2
        mock_sleep.assert_called_once_with(3)

    @patch("requests.post")
    @patch("requests.get")
    def test_scan_workflow_with_threat_detected(self, mock_get, mock_post):
        """Test workflow when threats are detected."""
        # Mock launch scan response
        mock_launch_response = Mock()
        mock_launch_response.status_code = 200
        mock_launch_response.json.return_value = {"scanID": "scan_threat_123", "status": "launched"}
        mock_launch_response.raise_for_status.return_value = None
        mock_post.return_value = mock_launch_response

        # Mock completed response with threats
        mock_completed_response = Mock()
        mock_completed_response.status_code = 200
        mock_completed_response.json.return_value = {
            "scanID": "scan_threat_123",
            "status": "Done",
            "artifact": "malicious.com",
            "scanResults": {
                "vt": {
                    "result": {
                        "data": {
                            "attributes": {
                                "last_analysis_stats": {
                                    "malicious": 12,
                                    "suspicious": 0,
                                    "undetected": 28,
                                    "harmless": 54,
                                },
                                "reputation": -60,
                            }
                        }
                    }
                },
                "mesmer": {
                    "result": {
                        "globalScore": "9",
                        "tags": [
                            {"value": "Trojan", "color": "red"},
                            {"value": "Malware", "color": "red"},
                        ],
                    }
                },
            },
        }
        mock_completed_response.raise_for_status.return_value = None
        mock_get.return_value = mock_completed_response

        # Execute workflow
        scan_id, _ = self.manager.launch_scan(self.test_artifact)
        result = self.manager.poll_scan_result(scan_id)

        assert result["status"] == "Done"
        assert (
            result["scanResults"]["vt"]["result"]["data"]["attributes"]["last_analysis_stats"][
                "malicious"
            ]
            == 12
        )
        assert result["scanResults"]["vt"]["result"]["data"]["attributes"]["reputation"] == -60
        assert result["scanResults"]["mesmer"]["result"]["globalScore"] == "9"
        assert len(result["scanResults"]["mesmer"]["result"]["tags"]) == 2

    @patch("requests.post")
    @patch("requests.get")
    def test_scan_workflow_with_mixed_results(self, mock_get, mock_post):
        """Test workflow with mixed scanner results."""
        # Mock launch scan response
        mock_launch_response = Mock()
        mock_launch_response.status_code = 200
        mock_launch_response.json.return_value = {"scanID": "scan_mixed_123", "status": "launched"}
        mock_launch_response.raise_for_status.return_value = None
        mock_post.return_value = mock_launch_response

        # Mock completed response with mixed results
        mock_completed_response = Mock()
        mock_completed_response.status_code = 200
        mock_completed_response.json.return_value = {
            "scanID": "scan_mixed_123",
            "status": "Done",
            "artifact": "test.com",
            "scanResults": {
                "vt": {
                    "result": {
                        "data": {
                            "attributes": {
                                "last_analysis_stats": {
                                    "malicious": 2,
                                    "suspicious": 1,
                                    "undetected": 25,
                                    "harmless": 52,
                                },
                                "reputation": -5,
                            }
                        }
                    }
                },
                "urlscan": {
                    "result": {"results": [{"page": {"status": "200", "domain": "test.com"}}]}
                },
                "abuseipdb": {
                    "result": {"abuseConfidenceScore": 15, "totalReports": 2, "isTor": False}
                },
            },
        }
        mock_completed_response.raise_for_status.return_value = None
        mock_get.return_value = mock_completed_response

        # Execute workflow
        scan_id, _ = self.manager.launch_scan(self.test_artifact, ["vt", "urlscan", "abuseipdb"])
        result = self.manager.poll_scan_result(scan_id)

        assert result["status"] == "Done"
        assert result["scanResults"]["vt"]["result"]["data"]["attributes"]["reputation"] == -5
        assert (
            result["scanResults"]["vt"]["result"]["data"]["attributes"]["last_analysis_stats"][
                "malicious"
            ]
            == 2
        )
        assert result["scanResults"]["abuseipdb"]["result"]["abuseConfidenceScore"] == 15
        assert result["scanResults"]["abuseipdb"]["result"]["isTor"] is False


if __name__ == "__main__":
    pytest.main([__file__])
