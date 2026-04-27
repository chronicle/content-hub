from __future__ import annotations
from TIPCommon import dict_to_flat


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


class Record(BaseModel):
    def __init__(self, raw_data):
        super(Record, self).__init__(raw_data)


class Table(BaseModel):
    def __init__(self, raw_data, id, name):
        super(Table, self).__init__(raw_data)
        self.name = name
        self.id = id

    def to_csv(self):
        return dict_to_flat({"ID": self.id, "Name": self.name})
