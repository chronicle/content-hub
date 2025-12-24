"""Simple demonstration of HoudinManager scan functionality using test.com."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from ..core.houdin import HoudinManager


class TestHoudinWithTestArtifact:
    """Demonstration tests using test.com artifact."""

    def setup_method(self):
        """Set up test fixtures."""
        self.api_key = "demo_api_key"
        self.manager = HoudinManager(api_key=self.api_key)
        self.test_artifact = "test.com"

    @patch("requests.post")
    @patch("requests.get")
    @patch("time.sleep")
    def test_scan_test_com_basic_workflow(self, mock_sleep, mock_get, mock_post):
        """Test basic scan workflow with test.com artifact using real Houdin response format."""
        # Mock successful scan launch
        mock_launch_response = Mock()
        mock_launch_response.status_code = 200
        mock_launch_response.json.return_value = {
            "scanID": "houdin-12345678-abcd-4321-test-com",
            "status": "launched",
        }
        mock_launch_response.raise_for_status.return_value = None
        mock_post.return_value = mock_launch_response

        # Mock completed scan result based on real Houdin format from YAML
        mock_completed_response = Mock()
        mock_completed_response.status_code = 200
        mock_completed_response.json.return_value = {
            "scanID": "houdin-12345678-abcd-4321-test-com",
            "clientID": "demo_client_id",
            "status": "Done",
            "artifact": "test.com",
            "scanOn": ["vt", "urlscan"],
            "scanResults": {
                "vt": {
                    "result": {
                        "data": {
                            "id": "test.com",
                            "type": "domain",
                            "attributes": {
                                "last_analysis_stats": {
                                    "malicious": 0,
                                    "suspicious": 0,
                                    "undetected": 3,
                                    "harmless": 85,
                                },
                                "reputation": 0,
                                "registrar": "Reserved Domain",
                            },
                        }
                    }
                },
                "urlscan": {
                    "result": {
                        "results": [
                            {
                                "page": {
                                    "domain": "test.com",
                                    "status": "200",
                                    "country": "US",
                                    "ip": "93.184.216.34",
                                }
                            }
                        ],
                        "total": 1,
                    }
                },
            },
            "scanTime": "2025-08-01T10:00:00Z",
        }
        mock_completed_response.raise_for_status.return_value = None
        mock_get.return_value = mock_completed_response

        # Execute the scan workflow
        scan_id, launch_status = self.manager.launch_scan(self.test_artifact)
        assert scan_id == "houdin-12345678-abcd-4321-test-com"
        assert launch_status == "launched"

        result = self.manager.poll_scan_result(scan_id)

        # Verify results match real Houdin format
        assert result["status"] == "Done"
        assert result["artifact"] == "test.com"
        assert (
            result["scanResults"]["vt"]["result"]["data"]["attributes"]["last_analysis_stats"][
                "malicious"
            ]
            == 0
        )
        assert result["scanResults"]["vt"]["result"]["data"]["attributes"]["reputation"] == 0
        assert (
            result["scanResults"]["urlscan"]["result"]["results"][0]["page"]["domain"] == "test.com"
        )

    @patch("requests.post")
    @patch("requests.get")
    def test_scan_test_com_with_vt_only(self, mock_get, mock_post):
        """Test scanning test.com with VT scanner only."""
        # Mock scan launch and result with VT only
        mock_launch_response = Mock()
        mock_launch_response.status_code = 200
        mock_launch_response.json.return_value = {"scanID": "houdin-vt-only", "status": "launched"}
        mock_launch_response.raise_for_status.return_value = None
        mock_post.return_value = mock_launch_response

        mock_completed_response = Mock()
        mock_completed_response.status_code = 200
        mock_completed_response.json.return_value = {
            "scanID": "houdin-vt-only",
            "status": "Done",
            "artifact": "test.com",
            "scanOn": ["vt"],
            "scanResults": {
                "vt": {
                    "result": {
                        "data": {
                            "attributes": {
                                "last_analysis_stats": {"malicious": 0, "harmless": 54},
                                "reputation": 0,
                            }
                        }
                    }
                }
            },
        }
        mock_completed_response.raise_for_status.return_value = None
        mock_get.return_value = mock_completed_response

        # Execute scan with VT only
        scan_id, _ = self.manager.launch_scan(self.test_artifact, ["vt"])
        result = self.manager.poll_scan_result(scan_id)

        assert result["artifact"] == "test.com"
        assert result["scanOn"] == ["vt"]
        assert (
            result["scanResults"]["vt"]["result"]["data"]["attributes"]["last_analysis_stats"][
                "malicious"
            ]
            == 0
        )

    @patch("requests.post")
    @patch("requests.get")
    @patch("time.sleep")
    def test_scan_test_com_with_malicious_result(self, mock_sleep, mock_get, mock_post):
        """Test scanning with malicious results (simulating malicious.com example from YAML)."""
        # Mock scan launch
        mock_launch_response = Mock()
        mock_launch_response.status_code = 200
        mock_launch_response.json.return_value = {
            "scanID": "houdin-malicious",
            "status": "launched",
        }
        mock_launch_response.raise_for_status.return_value = None
        mock_post.return_value = mock_launch_response

        # Mock malicious scan result based on YAML example
        mock_pending = Mock()
        mock_pending.status_code = 202

        mock_completed_response = Mock()
        mock_completed_response.status_code = 200
        mock_completed_response.json.return_value = {
            "scanID": "houdin-malicious",
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
        mock_get.side_effect = [mock_pending, mock_completed_response]

        # Execute scan
        scan_id, _ = self.manager.launch_scan("malicious.com", ["vt", "mesmer"])
        result = self.manager.poll_scan_result(scan_id)

        # Verify malicious detection
        assert result["status"] == "Done"
        assert result["scanResults"]["vt"]["result"]["data"]["attributes"]["reputation"] == -60
        assert (
            result["scanResults"]["vt"]["result"]["data"]["attributes"]["last_analysis_stats"][
                "malicious"
            ]
            == 12
        )
        assert result["scanResults"]["mesmer"]["result"]["globalScore"] == "9"
        assert len(result["scanResults"]["mesmer"]["result"]["tags"]) == 2

    def test_clean_scan_on_with_available_scanners(self):
        """Test cleanScanOn method with scanners from YAML."""
        # Test scanners from the YAML file
        yaml_scanners = [
            "vt",
            "urlscan",
            "alienvault",
            "abuseipdb",
            "triage",
            "mesmer",
            "servicenow",
        ]
        result = self.manager.cleanScanOn(yaml_scanners)
        assert result == yaml_scanners

        # Test mix of valid and invalid
        mixed = ["vt", "invalid_scanner", "urlscan"]
        result = self.manager.cleanScanOn(mixed)
        assert result == ["vt", "urlscan"]

        # Test empty result
        invalid = ["invalid1", "invalid2"]
        result = self.manager.cleanScanOn(invalid)
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__])
