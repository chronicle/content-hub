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

    def to_table(self):
        return dict_to_flat(self.to_json())

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Zone(BaseModel):
    def __init__(self, raw_data, zone_id):
        super(Zone, self).__init__(raw_data)
        self.zone_id = zone_id


class FirewallRule(BaseModel):
    def __init__(self, raw_data, id, description, action, filter):
        super(FirewallRule, self).__init__(raw_data)
        self.id = id
        self.description = description
        self.action = action
        self.filter = filter


class FirewallFilter(BaseModel):
    def __init__(self, raw_data, id, expression):
        super().__init__(raw_data)
        self.id = id
        self.expression = expression


class RuleList(BaseModel):
    def __init__(
        self,
        raw_data,
        id,
        name,
        kind,
        num_items,
        num_referencing_filters,
        created_on,
        modified_on,
    ):
        super().__init__(raw_data)
        self.rule_list_id = id
        self.name = name
        self.kind = kind
        self.num_items = num_items
        self.num_referencing_filters = num_referencing_filters
        self.created_on = created_on
        self.modified_on = modified_on


class RuleListItem(BaseModel):
    def __init__(self, raw_data):
        super().__init__(raw_data)
