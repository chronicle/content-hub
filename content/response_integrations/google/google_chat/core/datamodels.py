from __future__ import annotations
from TIPCommon import add_prefix_to_dict, dict_to_flat


class BaseModel:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_csv(self):
        return dict_to_flat(self.to_json())

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Message(BaseModel):
    def __init__(self, raw_data, **kwargs):
        super().__init__(raw_data)


class Spaces(BaseModel):
    def __init__(self, raw_data, name=None, **kwargs):
        super().__init__(raw_data)
        self.name = name


class Member(BaseModel):
    def __init__(self, raw_data, display_name, **kwargs):
        super().__init__(raw_data)
        self.display_name = display_name
