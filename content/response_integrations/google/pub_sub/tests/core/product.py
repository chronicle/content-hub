from __future__ import annotations
import abc

import dataclasses
import pathlib

from TIPCommon.types import SingleJson
from integration_testing.common import get_def_file_content


MOCK_DATA_PATH = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_DATA = get_def_file_content(MOCK_DATA_PATH)


@dataclasses.dataclass
class Product(abc.ABC):
    messages: list[SingleJson] = dataclasses.field(default_factory=dict)

    def set_messages(self, messages: list[SingleJson]):
        self.messages = messages

    def list_messages(self) -> list[SingleJson]:
        return self.messages
