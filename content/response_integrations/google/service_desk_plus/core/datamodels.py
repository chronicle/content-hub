from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Self

    from TIPCommon.types import SingleJson


@dataclasses.dataclass(slots=True)
class BaseModel:
    raw_data: SingleJson

    def to_json(self) -> SingleJson:
        return self.raw_data


@dataclasses.dataclass(slots=True)
class WorkOrder(BaseModel):
    workorderid: str

    @classmethod
    def from_json(cls, json_data: SingleJson) -> Self:
        return cls(
            raw_data=json_data,
            workorderid=json_data.get("workorderid"),
        )
