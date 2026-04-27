from __future__ import annotations
from TIPCommon.transformation import dict_to_flat, add_prefix_to_dict


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


class APIResponse:
    def __init__(self, raw_data=None):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_flat_dict(self):
        return dict_to_flat(self.to_dict())


class Request:
    def __init__(self, raw_data=None, status=None, orig_request=None):
        self.raw_data = raw_data
        self.status = status
        self.orig_request = orig_request

    def to_json(self):
        return self.raw_data

    def to_flat_dict(self):
        return dict_to_flat(self.to_dict())


class Note:
    def __init__(self, raw_data=None, notes=None, note_ids=None):
        self.raw_data = raw_data
        self.notes = notes
        self.note_ids = note_ids

    def to_json(self):
        return self.raw_data

    def to_flat_dict(self):
        return dict_to_flat(self.to_dict())
