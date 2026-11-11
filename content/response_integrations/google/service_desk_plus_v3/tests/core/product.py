from __future__ import annotations
import abc
import dataclasses
from service_desk_plus_v3.core.datamodels import Request

@dataclasses.dataclass
class ServiceDeskPlusV3(abc.ABC):
    def __init__(self):
        super().__init__()
        self._requests: list[Request] = []

    @property
    def requests(self) -> list[Request]:
        return self._requests

    def add_request(self, request: Request) -> None:
        self._requests.append(request)

    def get_requests(self) -> list[Request]:
        return self._requests
