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

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class ResponseObject(BaseModel):
    def __init__(self, raw_data, command, message, code):
        super(ResponseObject, self).__init__(raw_data)
        self.command = command
        self.message = message
        self.code = code


class IPObject(BaseModel):
    def __init__(self, raw_data, name, uuid, zone, ip):
        super(IPObject, self).__init__(raw_data)
        self.raw_data = raw_data
        self.name = name
        self.uuid = uuid
        self.zone = zone
        self.ip = ip


class AddressGroup(BaseModel):
    def __init__(self, raw_data, name, uuid, address_objects):
        super(AddressGroup, self).__init__(raw_data)
        self.name = name
        self.uuid = uuid
        self.address_objects = address_objects

    def to_row_data(self):
        return {"UUID": self.uuid, "Name": self.name}


class URIListObject(BaseModel):
    def __init__(self, raw_data, name, uri_list):
        super(URIListObject, self).__init__(raw_data)
        self.name = name
        self.uri_list = uri_list


class URIObject(BaseModel):
    def __init__(self, raw_data, uri):
        super(URIObject, self).__init__(raw_data)
        self.uri = uri


class URIListGroupObject(BaseModel):
    def __init__(self, raw_data, name):
        super(URIListGroupObject, self).__init__(raw_data)
        self.name = name


class URIGroupObject(BaseModel):
    def __init__(self, raw_data, name, uri_list, uri_group):
        super(URIGroupObject, self).__init__(raw_data)
        self.name = name
        self.uri_list = uri_list
        self.uri_group = uri_group
