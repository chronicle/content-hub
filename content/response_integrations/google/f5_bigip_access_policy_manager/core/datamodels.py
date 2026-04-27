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


class ActiveSessionObject(BaseModel):

    def __init__(self, raw_data, active_session_id, stats, client_ip, logon_user):
        super(ActiveSessionObject, self).__init__(raw_data)
        self.active_session_id = active_session_id
        self.stats = stats
        self.client_ip = client_ip
        self.logon_user = logon_user

    def to_json(self):
        json_data = {}
        if self.active_session_id:
            json_data["sessionID"] = self.active_session_id

        if self.stats:
            json_data["nestedStats"] = self.stats

        return json_data
