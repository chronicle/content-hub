import pathlib
import urllib.parse

from scc_enterprise.core.GoogleSecurityCommandCenterConstants import (
    ENDPOINTS
)
from scc_enterprise.core.GoogleSecurityCommandCenterManager import (
    GoogleSecurityCommandCenterManager
)
from scc_enterprise.tests.core.product import GoogleSecurityCommandCenter
from scc_enterprise.tests.core.session import (
    GoogleSecurityCommandCenterSession
)

from integration_testing.common import get_def_file_content
from integration_testing.requests.session import HistoryRecord
from integration_testing.set_meta import set_metadata

MOCK_DATA_PATH = pathlib.Path(__file__).parent / 'mock_data.json'
MOCK_DATA = get_def_file_content(MOCK_DATA_PATH)


@set_metadata
def test_connectivity(
        script_session: GoogleSecurityCommandCenterSession,
        google_security_command_center_manager: GoogleSecurityCommandCenterManager
):
    """Test connectivity call."""
    result = google_security_command_center_manager.test_connectivity()

    assert result
    assert len(script_session.request_history) == 2
    assert all(
        request.request.kwargs.get('headers', {})
        .get('SCC-Client-Context') == 'SOAR'
        for request in script_session.request_history
    )
    assert (
        script_session.request_history[0].request.url.path[1:]
        == ENDPOINTS['ping'].format(
            id=google_security_command_center_manager.organization_id,
            location_id=google_security_command_center_manager.location_id
        ).split('?')[0]
    )


@set_metadata
def test_list_findings(
        script_session: GoogleSecurityCommandCenterSession,
        google_security_command_center_product: GoogleSecurityCommandCenter,
        google_security_command_center_manager: GoogleSecurityCommandCenterManager
):
    """Test list findings."""
    filter_string = 'name:""'
    google_security_command_center_product.add_finding(
        MOCK_DATA['aws_finding']
    )

    findings = google_security_command_center_manager.list_findings_by_filter(
        filter_string
    )

    assert findings
    assert len(script_session.request_history) == 2
    assert all(
        record.request.kwargs.get('headers', {})
        .get('SCC-Client-Context') == 'SOAR'
        for record in script_session.request_history
    )
    assert (
        script_session.request_history[-1].request.url.path[1:]
        == ENDPOINTS['list_findings'].format(
            id=google_security_command_center_manager.organization_id,
            location_id=google_security_command_center_manager.location_id
        ).split('?')[0]
    )
    assert (
        f'filter={urllib.parse.quote(filter_string)}'
        in script_session.request_history[-1].request.url.query
    )


@set_metadata
def test_list_sources(
        script_session: GoogleSecurityCommandCenterSession,
        google_security_command_center_product: GoogleSecurityCommandCenter,
        google_security_command_center_manager: GoogleSecurityCommandCenterManager
):
    """Test list sources."""
    google_security_command_center_product.add_source(
        MOCK_DATA['source']
    )

    sources = google_security_command_center_manager.list_sources()

    assert sources
    assert len(script_session.request_history) == 2
    assert all(
        request.request.kwargs.get('headers', {})
        .get('SCC-Client-Context') == 'SOAR'
        for request in script_session.request_history
    )
    assert (
        script_session.request_history[-1].request.url.path[1:]
        == ENDPOINTS['list_sources'].format(
            id=google_security_command_center_manager.organization_id,
        ).split('?')[0]
    )


@set_metadata
def test_get_finding_details(
        script_session: GoogleSecurityCommandCenterSession,
        google_security_command_center_product: GoogleSecurityCommandCenter,
        google_security_command_center_manager: GoogleSecurityCommandCenterManager
):
    """Test get finding's details."""
    google_security_command_center_product.add_finding(
        MOCK_DATA['aws_finding']
    )

    finding = google_security_command_center_manager.get_finding_details(
        MOCK_DATA['aws_finding']['finding']['name']
    )

    assert finding
    assert len(script_session.request_history) == 2
    assert all(
        request.request.kwargs.get('headers', {})
        .get('SCC-Client-Context') == 'SOAR'
        for request in script_session.request_history
    )
    assert (
        script_session.request_history[-1].request.url.path[1:]
        == ENDPOINTS['get_finding_details'].format(
            id=google_security_command_center_manager.organization_id,
            location_id=google_security_command_center_manager.location_id,
            finding_name=MOCK_DATA['aws_finding']['finding']['name']
        ).split('?')[0]
    )
    assert (
        f'filter=name="{MOCK_DATA["aws_finding"]["finding"]["name"]}"'
        in script_session.request_history[-1].request.url.query
    )


@set_metadata
def test_update_finding_external_systems(
        script_session: GoogleSecurityCommandCenterSession,
        google_security_command_center_product: GoogleSecurityCommandCenter,
        google_security_command_center_manager: GoogleSecurityCommandCenterManager
):
    """Test patch finding's externalSystems."""
    google_security_command_center_product.add_finding(
        MOCK_DATA['aws_finding']
    )

    google_security_command_center_manager.update_finding_external_systems(
        external_system_name=(
            f'{MOCK_DATA["aws_finding"]["finding"]["name"]}/externalSystems'
        )
    )

    assert len(script_session.request_history) == 2
    assert all(
        request.request.kwargs.get('headers', {})
        .get('SCC-Client-Context') == 'SOAR'
        for request in script_session.request_history
    )
    assert (
        script_session.request_history[-1].request.url.path[1:]
        == ENDPOINTS['update_finding_external_systems'].format(
            external_system_name=(
                f'{MOCK_DATA["aws_finding"]["finding"]["name"]}/externalSystems'
            )
        ).split('?')[0]
    )


class TestGetOrUpdateNotificationConfig:
    @staticmethod
    def _assert_get_config_call(
            record: HistoryRecord,
            google_security_command_center_manager: GoogleSecurityCommandCenterManager,
            test_config_name: str,
            status_code: int
    ):
        assert (
            record.request.url.path[1:]
            == ENDPOINTS['get_notifications_config'].format(
                id=google_security_command_center_manager.organization_id,
                location_id=google_security_command_center_manager.location_id,
                notifications_config_id=test_config_name
            ).split('?')[0]
        )
        assert record.response.status_code == status_code

    @staticmethod
    def _assert_create_config_call(
            record: HistoryRecord,
            google_security_command_center_manager: GoogleSecurityCommandCenterManager,
            test_config_name: str
    ):
        assert (
            record.request.url.path[1:]
            == ENDPOINTS['create_notifications_config'].format(
                id=google_security_command_center_manager.organization_id,
                location_id=google_security_command_center_manager.location_id
            ).split('?')[0]
        )
        assert f'configId={test_config_name}' in record.request.url.query
        assert record.response.status_code == 200

    @staticmethod
    def _assert_delete_config_call(
            record: HistoryRecord,
            google_security_command_center_manager: GoogleSecurityCommandCenterManager,
            test_config_name: str
    ):
        assert (
            record.request.url.path[1:]
            == ENDPOINTS['delete_legacy_notifications_config'].format(
                id=google_security_command_center_manager.organization_id,
                notifications_config_id=test_config_name
            ).split('?')[0]
        )

    @staticmethod
    def _assert_patch_config_call(
            record: HistoryRecord,
            google_security_command_center_manager: GoogleSecurityCommandCenterManager,
            test_config_name: str
    ):
        test_config_full_name = (
            f'organizations/{google_security_command_center_manager.organization_id}'
            f'/locations/{google_security_command_center_manager.location_id}'
            f'/notificationConfigs/{test_config_name}'
        )
        assert (
            record.request.url.path[1:]
            == ENDPOINTS['patch_notifications_config'].format(
                notification_config_name=test_config_full_name
            ).split('?')[0]
        )

    @set_metadata
    def test_get_or_update_notification_config(
        self,
        script_session: GoogleSecurityCommandCenterSession,
        google_security_command_center_manager: GoogleSecurityCommandCenterManager
    ):
        """Test get or update notification config.

        First run:
        1. Get config request with 404 in response
        2. Create config request

        Second run:
        4. Get config request finds a config
        5. Patch request to update config
        """
        test_config_name = 'test-notifications-config'

        google_security_command_center_manager._get_or_update_notification_config(
            notifications_config_name=test_config_name,
            query_filter='test-query-filter',
            pubsub_topic='projects/test-project/topics/test-topic'
        )
        assert len(script_session.request_history) == 3
        assert all(
            request.request.kwargs.get('headers', {})
            .get('SCC-Client-Context') == 'SOAR'
            for request in script_session.request_history
        )
        self._assert_get_config_call(
            script_session.request_history[1],
            google_security_command_center_manager,
            test_config_name,
            status_code=404
        )
        self._assert_create_config_call(
            script_session.request_history[2],
            google_security_command_center_manager,
            test_config_name,
        )
        script_session.request_history.clear()

        google_security_command_center_manager._get_or_update_notification_config(
            notifications_config_name=test_config_name,
            query_filter='test-query-filter-updated',
            pubsub_topic='projects/test-project/topics/test-topic'
        )
        assert len(script_session.request_history) == 2
        assert all(
            request.request.kwargs.get('headers', {})
            .get('SCC-Client-Context') == 'SOAR'
            for request in script_session.request_history
        )
        self._assert_get_config_call(
            script_session.request_history[0],
            google_security_command_center_manager,
            test_config_name,
            status_code=200
        )
        self._assert_patch_config_call(
            script_session.request_history[1],
            google_security_command_center_manager,
            test_config_name
        )
