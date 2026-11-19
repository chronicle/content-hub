from __future__ import annotations
import abc

import dataclasses


@dataclasses.dataclass
class Product(abc.ABC):
    _threat_types_map: dict[str, list[str]] = dataclasses.field(default_factory=dict)

    def add_uri(self, uri: str, threat_types: list[str]) -> None:
        self._threat_types_map[uri] = threat_types

    def get_threat_types(self, uri: str) -> list[str]:
        return self._threat_types_map.get(uri)
