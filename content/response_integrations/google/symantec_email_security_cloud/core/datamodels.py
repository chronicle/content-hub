from __future__ import annotations
from TIPCommon import dict_to_flat, add_prefix_to_dict


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_table(self):
        return dict_to_flat(self.to_json())

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class IOCResult(BaseModel):
    def __init__(self, raw_data, blacklist_id, ioc_type, ioc_value, failure_reason):
        super(IOCResult, self).__init__(raw_data)
        self.blacklist_id = blacklist_id
        self.ioc_type = ioc_type
        self.ioc_value = ioc_value
        self.failure_reason = failure_reason
