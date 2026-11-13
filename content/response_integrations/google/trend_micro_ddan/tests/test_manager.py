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
import unittest
from unittest.mock import Mock, patch
import pytest
import requests
from trend_micro_ddan.core import TrendMicroDDANExceptions
from trend_micro_ddan.core.TrendMicroDDANManager import TrendMicroDDANManager
from trend_micro_ddan.core.TrendMicroDDANExceptions import TrendMicroDDANException
from trend_micro_ddan.core.UtilsManager import get_string_sha1
from trend_micro_ddan.core.constants import SAMPLE_TYPE
from trend_micro_ddan.core.datamodels import Report, EventLog, SuspiciousObject

FILE_URL = "https://www.clickdimensions.com/links/TestPDFfile.pdf"
LIMIT = 1
HTML_TEXT = """
    <Return>
    <head>
        <title>Sample HTML</title>
    </head>
    <body>
        <h1>This is a Sample HTML</h1>
        <p>This is a paragraph with some text.</p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
            <li>Item 3</li>
        </ul>
    </body>
    <REPORTS>
        <REPORT>
            <li>Item 1</li>
            <li>Item 2</li>
            <li>Item 3</li>
        </REPORT>
    </REPORTS>
    </Return>
"""


class TestTrendMicroDDANManager(unittest.TestCase):
    def setUp(self) -> None:
        with open(pathlib.Path(__file__).parent / "config.json", "r") as f:
            data = f.read()

        config = json.loads(data)

        api_root = config.get("API Root")
        api_key = config.get("API Key")
        if isinstance(config.get("Verify SSL"), str):
            verify_ssl = (
                True if config.get("Verify SSL").lower() == "true" else False
            )
        else:
            verify_ssl = config.get("Verify SSL")

        self.manager = TrendMicroDDANManager(
            api_root,
            api_key,
            verify_ssl
        )

    @pytest.mark.usefixtures("mock_get_request_with_return_none")
    def test_connectivity_success(self) -> None:
        """
        Test for connectivity success
        Returns:
            None
        """
        self.manager.register()
        result = self.manager.test_connectivity()
        self.manager.unregister()
        assert result is None

    @pytest.mark.usefixtures("mock_test_connectivity_to_raise_manager_error")
    def test_connectivity_fail(self) -> None:
        """
        Test for connectivity failure
        Returns:
            None
        """
        with pytest.raises(TrendMicroDDANException):
            self.manager.test_connectivity()

    @pytest.mark.usefixtures("mock_get_request_with_return_none")
    def test_register_success(self) -> None:
        """
        Test for register success
        Returns:
            None
        """
        result = self.manager.register()
        self.manager.unregister()
        assert result is True

    @pytest.mark.usefixtures("mock_register_to_raise_manager_error")
    def test_register_fail(self) -> None:
        """
        Test for register failure
        Returns:
            None
        """
        with pytest.raises(TrendMicroDDANException):
            self.manager.register()

    @pytest.mark.usefixtures("mock_get_request_with_return_none")
    def test_unregister_success(self) -> None:
        """
        Test for unregister success
        Returns:
            None
        """
        result = self.manager.unregister()
        assert result is None

    @pytest.mark.usefixtures("mock_unregister_to_raise_manager_error")
    def test_unregister_fail(self) -> None:
        """
        Test for unregister failure
        Returns:
            None
        """
        with pytest.raises(TrendMicroDDANException):
            self.manager.unregister()

    @pytest.mark.usefixtures("mock_get_request_with_return_none")
    def test_check_duplicate_success(self) -> None:
        """
        Test for check duplicate success
        Returns:
            None
        """
        mock_response = Mock()
        mock_response.text = "Success"
        patch_object = patch.object(
            self.manager.session, "put", return_value=mock_response
        )
        with patch_object:
            self.manager.register()
            result = self.manager.check_duplicate(FILE_URL)
            self.manager.unregister()
            assert isinstance(result, str)

    @pytest.mark.usefixtures("mock_check_duplicate_to_raise_manager_error")
    def test_check_duplicate_fail(self) -> None:
        """
        Test for check duplicate failure
        Returns:
            None
        """
        with pytest.raises(TrendMicroDDANException):
            self.manager.check_duplicate(FILE_URL)

    @pytest.mark.usefixtures("mock_get_request_with_return_none")
    @pytest.mark.usefixtures("mock_post_request_for_manager")
    def test_submit_sample_success(self) -> None:
        """
        Test for submit sample success
        Returns:
            None
        """
        self.manager.register()
        result = self.manager.submit_sample(get_string_sha1(FILE_URL), SAMPLE_TYPE.get("url"), FILE_URL)
        self.manager.unregister()
        assert result is None

    @pytest.mark.usefixtures("mock_submit_sample_to_raise_manager_error")
    def test_submit_sample_fail(self) -> None:
        """
        Test for submit sample failure
        Returns:
            None
        """
        with pytest.raises(TrendMicroDDANException):
            self.manager.submit_sample(get_string_sha1(FILE_URL), SAMPLE_TYPE.get("url"), FILE_URL)

    @pytest.mark.usefixtures("mock_get_request_with_return_none")
    def test_get_report_success(self) -> None:
        """
        Test for get report success
        Returns:
            None
        """
        self.manager.register()
        try:
            with patch.object(self.manager.session, 'get') as mock_get:
                mock_response = mock_get.return_value
                mock_response.text = HTML_TEXT
                mock_response.status_code = 200
                assert isinstance(self.manager.get_report(FILE_URL), Report)
        except TrendMicroDDANExceptions.TrendMicroDDANInProgressException:
            pass
        finally:
            self.manager.unregister()

    @pytest.mark.usefixtures("mock_get_report_to_raise_manager_error")
    def test_get_report_fail(self) -> None:
        """
        Test for get report failure
        Returns:
            None
        """
        with pytest.raises(TrendMicroDDANException):
            self.manager.get_report(FILE_URL)

    @pytest.mark.usefixtures("mock_get_request_with_return_none")
    def test_get_event_logs_success(self) -> None:
        """
        Test for get event logs success
        Returns:
            None
        """
        self.manager.register()
        with patch.object(self.manager.session, 'get') as mock_get:
            mock_response = mock_get.return_value
            mock_response.text = HTML_TEXT
            results = self.manager.get_event_logs(FILE_URL, LIMIT)
        self.manager.unregister()
        assert isinstance(results, list)

        for result in results:
            assert isinstance(result, EventLog)

    @pytest.mark.usefixtures("mock_get_event_logs_to_raise_manager_error")
    def test_get_event_logs_fail(self) -> None:
        """
        Test for get event logs failure
        Returns:
            None
        """
        with pytest.raises(TrendMicroDDANException):
            self.manager.get_event_logs(FILE_URL, LIMIT)

    @pytest.mark.usefixtures("mock_get_request_with_return_none")
    def test_get_suspicious_objects_success(self) -> None:
        """
        Test for get suspicious objects success
        Returns:
            None
        """
        self.manager.register()
        try:
            with patch.object(self.manager.session, 'get') as mock_get:
                mock_response = mock_get.return_value
                mock_response.text = HTML_TEXT
                results = self.manager.get_suspicious_objects(FILE_URL, LIMIT)
            assert isinstance(results, list)

            for result in results:
                assert isinstance(result, SuspiciousObject)

        except TrendMicroDDANExceptions.TrendMicroDDANNotFoundException:
            pass
        finally:
            self.manager.unregister()

    @pytest.mark.usefixtures("mock_get_suspicious_objects_to_raise_manager_error")
    def test_get_suspicious_objects_fail(self) -> None:
        """
        Test for get suspicious objects failure
        Returns:
            None
        """
        with pytest.raises(TrendMicroDDANException):
            self.manager.get_suspicious_objects(FILE_URL, LIMIT)

    @pytest.mark.usefixtures("mock_get_request_with_return_none")
    def test_get_screenshot_success(self) -> None:
        """
        Test for get screenshot success
        Returns:
            None
        """
        self.manager.register()
        try:
            result = self.manager.get_screenshot(FILE_URL)
            assert isinstance(result, str)

        except TrendMicroDDANExceptions.TrendMicroDDANNotFoundException:
            pass
        finally:
            self.manager.unregister()

    @pytest.mark.usefixtures("mock_get_screenshot_to_raise_manager_error")
    def test_get_screenshot_fail(self) -> None:
        """
        Test for get screenshot failure
        Returns:
            None
        """
        with pytest.raises(TrendMicroDDANException):
            self.manager.get_screenshot(FILE_URL)

