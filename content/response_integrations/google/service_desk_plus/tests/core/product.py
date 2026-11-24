from __future__ import annotations
import abc

import dataclasses

from service_desk_plus.core.datamodels import WorkOrder

@dataclasses.dataclass
class ServiceDeskPlus(abc.ABC):

    def __init__(self):
        super().__init__()
        self._requests: list[WorkOrder] = []
        self._add_request_mock: WorkOrder | None = None

    @property
    def requests(self) -> list[WorkOrder]:
        return self._requests

    def add_request(self, request: WorkOrder) -> None:
        self._requests.append(request)

    def get_requests(self) -> list[WorkOrder]:
        return self._requests

    def set_add_request_mock(self, request: WorkOrder) -> None:
        self._add_request_mock = request

    def get_add_request_mock(self) -> WorkOrder | None:
        return self._add_request_mock
