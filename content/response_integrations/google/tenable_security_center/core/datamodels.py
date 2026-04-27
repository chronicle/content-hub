from __future__ import annotations
class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data


class Scan(BaseModel):
    def __init__(self, raw_data):
        super(Scan, self).__init__(raw_data)


class IPListAsset(BaseModel):
    def __init__(self, raw_data, defined_ips):
        super(IPListAsset, self).__init__(raw_data)
        self.defined_ips = defined_ips


class EnrichIP(BaseModel):
    def __init__(self, raw_data):
        super(EnrichIP, self).__init__(raw_data)
