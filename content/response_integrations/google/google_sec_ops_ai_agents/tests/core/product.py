import abc
import contextlib


class GoogleSecOpsAiAgents(abc.ABC):
    """GoogleSecOpsAiAgents mock product"""

    def __init__(self) -> None:
        super().__init__()
        self._investigations: dict[str, list] = {}
        self._triggered_investigations: dict[str, dict] = {}
        self._investigation_statuses: dict[str, dict] = {}
        self._fail_requests_active: bool = False

    @contextlib.contextmanager
    def fail_requests(self):
        """Context manager to simulate API failures"""
        self._fail_requests_active = True
        try:
            yield
        finally:
            self._fail_requests_active = False

    def add_investigations(self, alert_id: str, investigations: list) -> None:
        """Add investigations to the mock product"""
        self._investigations[alert_id] = investigations

    def get_investigations(self, alert_id: str) -> list:
        """Get investigations from the mock product"""
        return self._investigations.get(alert_id, [])

    def cleanup_investigations(self) -> None:
        """Cleanup investigations from the mock product"""
        self._investigations = {}

    def add_triggered_investigation(self, alert_id: str, investigation_data: dict) -> None:
        """Add a triggered investigation to the mock product"""
        self._triggered_investigations[alert_id] = investigation_data

    def trigger_investigation(self, alert_id: str) -> dict:
        """Trigger an investigation in the mock product"""
        return self._triggered_investigations.get(alert_id, {})

    def add_investigation_status(self, investigation_name: str, status_data: dict) -> None:
        """Add an investigation status to the mock product"""
        self._investigation_statuses[investigation_name] = status_data

    def get_investigation_status(self, investigation_name: str) -> dict:
        """Get an investigation status from the mock product"""
        return self._investigation_statuses.get(investigation_name, {})
