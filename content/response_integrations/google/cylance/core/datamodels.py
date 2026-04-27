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


class DownloadLink(BaseModel):
    def __init__(self, raw_data, url):
        super(DownloadLink, self).__init__(raw_data)
        self.url = url

    def to_enrichment_data(self, prefix=None):
        data = {"dl": self.url}
        data = dict_to_flat(data)
        return add_prefix_to_dict(data, prefix) if prefix else data
