from __future__ import annotations
class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data


class QueryStatus(BaseModel):
    def __init__(self, raw_data, status, result_type, hit, scanned, elapsed, message):
        super(QueryStatus, self).__init__(raw_data)
        self.status = status
        self.result_type = result_type
        self.hit = hit
        self.scanned = scanned
        self.elapsed = elapsed
        self.message = message
