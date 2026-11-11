from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Self

    from TIPCommon.types import SingleJson


@dataclass(slots=True)
class IntegrationParameters:
    api_root: str
    client_id: str
    client_secret: str
    verify_ssl: bool
    cluster_id: str


@dataclass(frozen=True, slots=True)
class Entry:
    raw_data: SingleJson
    attribute: str
    operator: str
    value: str
    comment: str | None

    @classmethod
    def from_json(cls, data: SingleJson) -> Self:
        return cls(
            raw_data=data,
            attribute=data.get("attribute", ""),
            operator=data.get("operator", ""),
            value=data.get("value", ""),
            comment=data.get("comment"),
        )

    def to_json(self) -> SingleJson:
        return self.raw_data


@dataclass(frozen=True, slots=True)
class AllowEntry(Entry):
    """Represents an allow list entry."""


@dataclass(frozen=True, slots=True)
class BlockEntry(Entry):
    """Represents an block list entry."""
