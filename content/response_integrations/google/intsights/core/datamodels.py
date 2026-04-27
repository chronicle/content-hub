from __future__ import annotations
import copy
from TIPCommon import convert_list_to_comma_string, dict_to_flat, add_prefix_to_dict


class BaseModel:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data


class Iocs(BaseModel):
    def __init__(self, raw_data, severity=None, **kwargs):
        super().__init__(raw_data=raw_data)
        self.severity = severity

    def to_enrichment_data(self, prefix=None):
        data = copy.deepcopy(self.raw_data)

        enrichment_data = {
            **data,
            "relatedCampaigns": convert_list_to_comma_string(
                data.get("relatedCampaigns", [])
            ),
            "relatedThreatActors": convert_list_to_comma_string(
                data.get("relatedThreatActors", [])
            ),
            "relatedMalware": convert_list_to_comma_string(
                data.get("relatedMalware", [])
            ),
            "tags": convert_list_to_comma_string(data.get("tags", [])),
            "reportedFeeds": convert_list_to_comma_string(
                [item.get("name") for item in data.get("reportedFeeds", [])]
            ),
        }

        return (
            add_prefix_to_dict(dict_to_flat(enrichment_data), prefix)
            if prefix
            else dict_to_flat(enrichment_data)
        )


class Alert(BaseModel):
    def __init__(
        self,
        raw_data,
        network_type=None,
        alert_type=None,
        severity=None,
        title=None,
        _id=None,
        FoundDate=None,
        **kwargs
    ):
        super().__init__(raw_data=raw_data)
        self.network_type = network_type
        self.alert_type = alert_type
        self.severity = severity
        self.title = title
        self.alert_id = _id
        self.found_date = FoundDate
