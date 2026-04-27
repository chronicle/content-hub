from __future__ import annotations
from soar_sdk.SiemplifyUtils import add_prefix_to_dict
import copy

ENRICH_PREFIX = "WhoisQuery_"


class Detail:
    """
    Detail class keeps information, which received from BulkWhoIs scanning
    """

    def __init__(self, raw_data=None, success=False, **kwargs):
        self.raw_data = raw_data
        self.success = success
        self.__dict__.update(kwargs)

    def to_json(self):
        return self.raw_data

    def to_enrichment_data(self):
        ret_dict = self.to_dict()
        return add_prefix_to_dict(ret_dict, ENRICH_PREFIX)

    def to_dict(self):
        ret_dict = copy.deepcopy(vars(self))
        del ret_dict["raw_data"]
        del ret_dict["success"]

        return ret_dict
