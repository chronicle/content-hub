from __future__ import annotations
from .constants import DIRECTION_MAPPER
from TIPCommon import dict_to_flat, add_prefix_to_dict


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data


class Entry(BaseModel):

    def __init__(
        self,
        raw_data,
        url,
        priority,
        weight,
        direction,
        start_port,
        end_port,
        note,
        is_regex,
    ):
        super(Entry, self).__init__(raw_data)
        self.url = url
        self.priority = priority
        self.weight = weight
        self.start_port = start_port
        self.end_port = end_port
        self.note = note
        self.is_regex = is_regex == 1
        try:
            self.direction = [
                direction_name
                for direction_name, direction_key in DIRECTION_MAPPER.items()
                if direction_key == direction
            ][0]
        except Exception:
            self.direction = ""

    def to_csv(self):
        return {
            "Name": self.url,
            "Priority": self.priority,
            "Weight": self.weight,
            "Direction": self.direction,
            "Start Port": self.start_port,
            "End Port": self.end_port,
            "Note": self.note,
            "Regex": self.is_regex,
        }


class Node(BaseModel):
    def __init__(self, raw_data, node_name, public_fqdn):
        super(Node, self).__init__(raw_data)
        self.node_name = node_name
        self.public_fqdn = public_fqdn

    def contains_valid_fqdn(self):
        return bool(self.public_fqdn)


class URL(BaseModel):

    def __init__(self, raw_data, action, categories, message):
        super(URL, self).__init__(raw_data)
        self.action = action
        self.categories = categories
        self.message = message

    def to_enrichment_data(self, prefix=None, group_id=None):

        if group_id:
            group_id = f"_{group_id}"

            new_dict = {
                f"group{group_id}_categories": self.action,
                f"group{group_id}_action": self.categories,
                f"group{group_id}_message": self.message,
            }
        else:
            new_dict = {
                "group_categories": self.action,
                "group_action": self.categories,
                "group_message": self.message,
            }

        data = dict_to_flat(new_dict)
        return add_prefix_to_dict(data, prefix) if prefix else data
