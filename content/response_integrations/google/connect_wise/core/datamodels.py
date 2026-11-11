from __future__ import annotations
class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data


class Attachment(BaseModel):
    def __init__(self, raw_data, **kwargs):
        super(Attachment, self).__init__(raw_data)
