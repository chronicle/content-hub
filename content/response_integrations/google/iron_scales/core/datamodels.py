from __future__ import annotations
class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data


class Incident(BaseModel):
    def __init__(self, raw_data, classification):
        super(Incident, self).__init__(raw_data)
        self.classification = classification


class Impersonation(BaseModel):
    def __init__(self, raw_data):
        super(Impersonation, self).__init__(raw_data)


class Mitigation(BaseModel):
    def __init__(self, raw_data):
        super(Mitigation, self).__init__(raw_data)
