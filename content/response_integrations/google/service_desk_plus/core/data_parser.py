from __future__ import annotations

from typing import TYPE_CHECKING

from service_desk_plus.core.datamodels import WorkOrder

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


def build_request(raw_data: SingleJson) -> WorkOrder:
    return WorkOrder.from_json(json_data=raw_data)
