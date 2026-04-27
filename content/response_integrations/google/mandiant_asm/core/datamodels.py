from __future__ import annotations
import copy
import json

from TIPCommon import dict_to_flat, add_prefix_to_dict
from TIPCommon.data_models import BaseAlert
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time


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


class Issue(BaseModel):
    def __init__(self, raw_data, name: str):
        super().__init__(raw_data)
        self.name = name


class ASMEntity(BaseModel):
    def __init__(self, raw_data, name: str):
        super().__init__(raw_data)
        self.name = name


class ConnectorIssue(BaseAlert):
    def __init__(
        self,
        raw_data,
        issue_id=None,
        pretty_name=None,
        proof=None,
        description=None,
        severity=None,
        category=None,
        first_seen=None,
        last_seen=None,
    ):
        super(ConnectorIssue, self).__init__(raw_data, issue_id)
        self.flat_raw_data = dict_to_flat(raw_data)
        self.issue_id = issue_id
        self.pretty_name = pretty_name
        self.proof = proof
        self.description = description
        self.severity = severity
        self.category = category
        self.first_seen = first_seen
        self.last_seen = last_seen
        self.first_seen_ms = convert_string_to_unix_time(first_seen)

    def to_events(self):
        event_data = copy.deepcopy(self.raw_data)

        if event_data.get("identifiers", []):
            identifier_count = {}

            for identifier in event_data.get("identifiers", []):
                if not event_data.get(identifier.get("type")):
                    identifier_count[identifier.get("type")] = 1
                else:
                    identifier_count[identifier.get("type")] += 1

                event_data[
                    f"{identifier.get('type')}_{identifier_count.get(identifier.get('type'))}"
                ] = identifier.get("name")

        event_data[event_data.get("entity_type").replace("::", "_")] = event_data.get(
            "entity_name"
        )

        if event_data.get("details").get("references"):

            event_data["references_json_string"] = json.dumps(
                event_data.get("details").get("references")
            )

        if self.proof:
            if type(self.proof) == str:
                event_data["proof"] = self.proof
            else:
                event_data["proof"] = json.dumps(self.proof)

        return [dict_to_flat(event_data)]
