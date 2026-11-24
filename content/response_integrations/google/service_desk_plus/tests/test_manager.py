from __future__ import annotations

import pytest

from service_desk_plus.core.ServiceDeskPlusManager import ServiceDeskPlusManager, ServiceDeskPlusManagerError
from service_desk_plus.core.datamodels import WorkOrder

class TestServiceDeskPlusManager:

    def test_test_connectivity_success(
        self,
        manager: ServiceDeskPlusManager,
    ) -> None:
        assert manager.test_connectivity() is True

    def test_test_connectivity_failure(
        self,
        manager: ServiceDeskPlusManager,
    ) -> None:
        manager.api_url_base = "https://invalid.url"
        with pytest.raises(ServiceDeskPlusManagerError):
            manager.test_connectivity()

    def test_add_request_success(
        self,
        manager: ServiceDeskPlusManager,
    ) -> None:
        result: WorkOrder = manager.add_request(
            subject="Test Subject",
            requester="Test Requester",
        )
        assert result is not None
        assert result.raw_data["workorderid"] == "12345"

    def test_add_request_failure(
        self,
        manager: ServiceDeskPlusManager,
    ) -> None:
        with pytest.raises(ServiceDeskPlusManagerError):
            manager.add_request(subject="FailSubject")
