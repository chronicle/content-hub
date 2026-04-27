from __future__ import annotations
from TIPCommon import dict_to_flat, add_prefix_to_dict
from .constants import MAX_LENGTH_FOR_JSON_RESULT_STRING


class BaseModel:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_flat(self):
        return dict_to_flat(self.to_json())

    def to_csv(self):
        return self.to_flat()

    def is_empty(self):
        return not bool(self.raw_data)


class Threat(BaseModel):
    def __init__(
        self,
        raw_data,
        threat_id=None,
        severity=None,
        confidence=None,
        status=None,
        modified_ts=None,
        itype=None,
        expiration_ts=None,
        ip=None,
        feed_id=None,
        uuid=None,
        retina_confidence=None,
        trusted_circle_ids=None,
        source=None,
        latitude=None,
        type=None,
        description=None,
        names=None,
        threatscore=None,
        source_reported_confidence=None,
        org=None,
        asn=None,
        created_ts=None,
        tlp=None,
        country=None,
        longitude=None,
        subtype=None,
        **kwargs
    ):
        super().__init__(raw_data)
        self.threat_id = threat_id
        self.severity = severity
        self._confidence = confidence
        self.modified_ts = modified_ts
        self.status = status
        self.itype = itype
        self.expiration_ts = expiration_ts
        self.ip = ip
        self.feed_id = feed_id
        self.uuid = uuid
        self.retina_confidence = retina_confidence
        self.trusted_circle_ids = (
            ",".join([str(circle_id) for circle_id in trusted_circle_ids])
            if trusted_circle_ids
            else None
        )
        self.source = source
        self.latitude = latitude
        self.type = type
        self.description = description
        self.names = ",".join(names) if names else None
        self.threat_score = threatscore
        self.source_reported_confidence = source_reported_confidence
        self.org = org
        self.asn = asn
        self.created_ts = created_ts
        self.tlp = tlp
        self.country = country
        self.longitude = longitude
        self.subtype = subtype

    def to_csv(self):
        return {
            "Severity": self.severity,
            "Confidence": self.confidence,
            "Type": self.itype,
            "Status": self.status,
        }

    def get_enrichment_table(self, prefix=None):
        """
        Add prefix to results and enrich entity
        :param prefix: The prefix to add to the results
        """
        enrichment_table = {
            "id": self.threat_id,
            "status": self.status,
            "itype": self.itype,
            "expiration_time": self.expiration_ts,
            "ip": self.ip,
            "feed_id": self.feed_id,
            "confidence": self.confidence,
            "uuid": self.uuid,
            "retina_confidence": self.retina_confidence,
            "trusted_circle_ids": self.trusted_circle_ids,
            "source": self.source,
            "latitude": self.latitude,
            "type": self.type,
            "description": self.description,
            "tags": self.names,
            "threat_score": self.threat_score,
            "source_confidence": self.source_reported_confidence,
            "modification_time": self.modified_ts,
            "org_name": self.org,
            "asn": self.asn,
            "creation_time": self.created_ts,
            "tlp": self.tlp,
            "country": self.country,
            "longitude": self.longitude,
            "severity": self.severity,
            "subtype": self.subtype,
        }
        result = {key: value for key, value in enrichment_table.items() if value}

        if prefix:
            return add_prefix_to_dict(result, prefix)

        return result

    @property
    def is_active(self):
        return self.status == "active"

    @property
    def is_falsepos(self):
        return self.status == "falsepos"

    @property
    def confidence(self):
        return self._confidence if self._confidence is not None else 0

    @property
    def severity_score(self):
        severity_mapping = {"low": 1, "medium": 2, "high": 3, "very-high": 4}

        return severity_mapping.get(self.severity, -1)


class Indicator(BaseModel):
    def __init__(self, raw_data, id=None, **kwargs):
        super().__init__(raw_data)
        self.id = id


class Associations(BaseModel):
    def __init__(self, raw_data, id=None, modified_ts=None, **kwargs):
        super().__init__(raw_data)
        self.id = id
        self.modified_ts = modified_ts


class AssociationDetails(BaseModel):
    def __init__(
        self, raw_data, status_display_name=None, id=None, name=None, **kwargs
    ):
        super().__init__(raw_data)
        self.display_name = status_display_name
        self.id = id
        self.name = name

    def to_json(self):
        data = self.raw_data
        # Shorten raw description
        if isinstance(data.get("description", ""), str):
            splitted = " ".join(
                data.get("description", "").split(" ")[
                    :MAX_LENGTH_FOR_JSON_RESULT_STRING
                ]
            )
            if splitted:
                data["description"] = splitted + "..."
            else:
                data["description"] = ""

        # Shorten raw body
        if isinstance(data.get("body", ""), str):
            splitted = " ".join(
                data.get("body", "").split(" ")[:MAX_LENGTH_FOR_JSON_RESULT_STRING]
            )
            if splitted:
                data["body"] = splitted + "..."
            else:
                data["body"] = ""

        return data

    def to_table(self, association_type):
        return {
            "ID": self.id,
            "Name": self.name,
            "Type": association_type,
            "Status": self.display_name,
        }
