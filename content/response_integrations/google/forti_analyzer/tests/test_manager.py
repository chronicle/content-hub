from __future__ import annotations

import json
import os
import unittest
from unittest.mock import Mock, patch

import pytest
from dateutil.relativedelta import relativedelta

from soar_sdk.SiemplifyUtils import utc_now

from forti_analyzer.core.datamodels import Device, Alert, AlertCommentResponse
from forti_analyzer.core.FortiAnalyzerExceptions import FortiAnalyzerException
from forti_analyzer.core.FortiAnalyzerManager import FortiAnalyzerManager

# CONSTANTS
IP = "172.30.203.248"
HOSTNAME = "FortiGate-VM64"
ALERT_ID = "202210131000040003"
ADOM = "root"
USERNAME = "api_user"

MOCK_DATA = json.load(
    open(
        os.path.join(os.path.dirname(__file__), "mock_data.json")
    )
)


class TestFortiAnalyzerManager(unittest.TestCase):
    def setUp(self) -> None:
        with open("config.json", "r") as f:
            data = f.read()

        config = json.loads(data)

        api_root = config.get("API Root")
        username = config.get("Username")
        password = config.get("Password")
        if isinstance(config.get("Verify SSL"), str):
            verify_ssl = (
                True if config.get("Verify SSL").lower() == "true" else False
            )
        else:
            verify_ssl = config.get("Verify SSL")
        with patch.object(FortiAnalyzerManager, 'login', return_value=Mock()):
            self.manager = FortiAnalyzerManager(
                api_root,
                username,
                password,
                verify_ssl
            )
        self.search_task_id = None

    def test_connectivity_success(self) -> None:
        """
        Test for connectivity success
        Returns:
            None
        """
        mock_post = Mock()
        mock_post.json.return_value = MOCK_DATA.get('/eventmgmt/alerts')
        with patch('requests.Session.post', return_value=mock_post):
            assert self.manager.test_connectivity() is None

    @pytest.mark.usefixtures("mock_test_connectivity_to_raise_manager_error")
    def test_connectivity_fail(self) -> None:
        """
        Test for connectivity failure
        Returns:
            None
        """
        with pytest.raises(FortiAnalyzerException):
            self.manager.test_connectivity()

    def test_get_device_with_ip(self) -> None:
        mock_response = Mock()
        mock_response.json.return_value = MOCK_DATA.get(
            'get_device_with_ip_or_hostname'
        )
        patch_object = patch.object(
            self.manager.session, "post", return_value=mock_response
        )
        with patch_object:
            device = self.manager.get_device(ip=IP, hostname='')
            assert isinstance(device, Device)

    def test_get_device_with_hostname(self) -> None:
        mock_response = Mock()
        mock_response.json.return_value = MOCK_DATA.get(
            'get_device_with_ip_or_hostname'
        )
        patch_object = patch.object(
            self.manager.session, "post", return_value=mock_response
        )
        with patch_object:
            device = self.manager.get_device(ip="", hostname=HOSTNAME)
            assert isinstance(device, Device)

    @pytest.mark.usefixtures("mock_get_device_raise_manager_error")
    def test_get_device_with_ip_fail(self) -> None:
        with pytest.raises(FortiAnalyzerException):
            self.manager.get_device(ip=IP, hostname='')

    @pytest.mark.usefixtures("mock_get_device_raise_manager_error")
    def test_get_device_with_hostname_fail(self) -> None:
        with pytest.raises(FortiAnalyzerException):
            self.manager.get_device(ip="", hostname=HOSTNAME)

    def test_find_alert(self) -> None:
        mock_response = Mock()
        mock_response.json.return_value = MOCK_DATA.get('find_alert')
        patch_object = patch.object(
            self.manager.session,
            "post",
            return_value=mock_response
        )
        with patch_object:
            alert = self.manager.find_alert(alert_id=ALERT_ID)
            assert isinstance(alert, Alert)

    @pytest.mark.usefixtures("mock_find_alert_raise_manager_error")
    def test_find_alert_fail(self) -> None:
        with pytest.raises(FortiAnalyzerException):
            self.manager.find_alert(alert_id=ALERT_ID)

    def test_mark_as_read(self) -> None:
        mock_response = Mock()
        mock_response.json.return_value = MOCK_DATA.get('mark_as_read')
        patch_object = patch.object(
            self.manager.session,
            "post",
            return_value=mock_response
        )
        with patch_object:
            assert self.manager.mark_as_read(alert_id=ALERT_ID, adom=ADOM)

    @pytest.mark.usefixtures("mock_mark_as_read_raise_manager_error")
    def test_mark_as_read_fail(self) -> None:
        with pytest.raises(FortiAnalyzerException):
            self.manager.mark_as_read(alert_id=ALERT_ID, adom=ADOM)

    def test_assign_user(self) -> None:
        mock_response = Mock()
        mock_response.json.return_value = MOCK_DATA.get('assign_user')
        patch_object = patch.object(
            self.manager.session,
            "post",
            return_value=mock_response
        )
        with patch_object:
            assert self.manager.assign_user(
                alert_id=ALERT_ID,
                adom=ADOM,
                username=USERNAME
            )

    @pytest.mark.usefixtures("mock_assign_user_raise_manager_error")
    def test_assign_user_fail(self) -> None:
        with pytest.raises(FortiAnalyzerException):
            self.manager.assign_user(alert_id=ALERT_ID, adom=ADOM, username=USERNAME)

    def test_acknowledge_alert(self) -> None:
        mock_response = Mock()
        mock_response.json.return_value = MOCK_DATA.get('acknowledge_alert', {})
        patch_object = patch.object(
            self.manager.session,
            "post",
            return_value=mock_response
        )
        with patch_object:
            result = self.manager.acknowledge_alert(
                alert_id=ALERT_ID,
                adom=ADOM,
                username=USERNAME,
                acknowledge=True
            )

        assert result == True

    @pytest.mark.usefixtures("mock_acknowledge_alert_raise_manager_error")
    def test_acknowledge_alert_fail(self) -> None:
        with pytest.raises(FortiAnalyzerException):
            self.manager.acknowledge_alert(
                alert_id=ALERT_ID,
                adom=ADOM,
                username=USERNAME,
                acknowledge=True
            )

    def test_add_comment_to_alert_success(self) -> None:
        """
        Test for add comment to alert success
        Returns:
            (): None
        """
        mock_response = Mock()
        mock_response.json.return_value = MOCK_DATA.get('add_comment_to_alert')
        patch_object = patch.object(
            self.manager.session,
            "post",
            return_value=mock_response
        )
        with patch_object:
            comment_response = self.manager.add_comment_to_alert(
                alert_id=ALERT_ID,
                adom=ADOM,
                comment="test comment"
            )
        assert isinstance(comment_response, AlertCommentResponse)

    @pytest.mark.usefixtures("mock_add_comment_to_alert_raise_manager_error")
    def test_add_comment_to_alert_fail(self) -> None:
        """
        Test for add comment to alert fail
        Returns:
            (): None
        """
        with pytest.raises(FortiAnalyzerException):
            self.manager.add_comment_to_alert(alert_id=ALERT_ID, adom=ADOM, comment="test comment")

    def test_search_log_task_creation(self) -> None:
        """
        Test for add creating search log task
        Returns:
            (): None
        """
        device_id = "All_Fortigate"  # default
        log_type = "Traffic"  # default
        is_case_sensitive = False
        query = ""
        start_time = utc_now() - relativedelta(months=1)
        # end_time = utc_now() - datetime.timedelta(days=1)  # timeframe: last 24 hours
        end_time = utc_now()
        time_order = "DESC"
        mock_response = Mock()
        mock_response.json.return_value = MOCK_DATA.get('create_search_task')
        patch_object = patch.object(
            self.manager.session,
            "post",
            return_value=mock_response
        )
        with patch_object:
            search_response = self.manager.create_search_task(
                log_type=log_type, is_case_sensitive=is_case_sensitive, device_id=device_id,
                query=query, start_time=start_time, end_time=end_time, time_order=time_order
            )
        self.assertIsInstance(search_response, int)

