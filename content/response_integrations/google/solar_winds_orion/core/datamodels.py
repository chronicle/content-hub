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


class QueryResult(BaseModel):
    def __init__(self, raw_data, ip_address, display_name):
        super(QueryResult, self).__init__(raw_data)
        self.ip_address = ip_address
        self.display_name = display_name

    def to_csv(self):
        return self.to_json()

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class ErrorObject(BaseModel):
    def __init__(self, raw_data, message):
        super(ErrorObject, self).__init__(raw_data)
        self.message = message
