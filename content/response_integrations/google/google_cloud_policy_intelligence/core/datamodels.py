from __future__ import annotations
from TIPCommon.data_models import BaseDataModel


class Activity(BaseDataModel):
    """Defines the structure for a Activity"""

    def __init__(self, raw_data: dict, resource_name: str):
        super().__init__(raw_data)
        self.resource_name = resource_name
