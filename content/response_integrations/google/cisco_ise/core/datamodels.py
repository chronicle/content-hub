from __future__ import annotations
import copy
from TIPCommon import flat_dict_to_csv, dict_to_flat


class BaseModel:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_flat(self):
        return dict_to_flat(self.to_json())

    def to_csv(self):
        return flat_dict_to_csv(self.to_flat())


class EndpointGroup(BaseModel):
    def __init__(self, raw_data, id, name, description):
        super(EndpointGroup, self).__init__(raw_data)
        self.id = id
        self.name = name
        self.description = description

    def to_json(self):
        json_dict = copy.deepcopy(self.raw_data)
        json_dict.pop("link", None)
        return json_dict

    def to_csv(self):
        return dict_to_flat({"Name": self.name, "Description": self.description})
