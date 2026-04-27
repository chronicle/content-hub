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

    def to_csv(self):
        return dict_to_flat(self.to_json())

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class RequestObject(BaseModel):
    def __init__(self, raw_data, id, redirect_url, status):
        super(RequestObject, self).__init__(raw_data)
        self.id = id
        self.redirect_url = redirect_url
        self.status = status


class Template(BaseModel):
    def __init__(self, raw_data, id, name, description, type):
        super(Template, self).__init__(raw_data)
        self.id = id
        self.name = name
        self.description = description
        self.type = type

    def to_csv(self):
        return dict_to_flat(
            {"Name": self.name, "Description": self.description, "Type": self.type}
        )
