from __future__ import annotations
from TIPCommon import dict_to_flat, add_prefix_to_dict, flat_dict_to_csv
from collections import defaultdict
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import convert_unixtime_to_datetime, unix_now
import copy
import uuid
from .constants import DATA_ENRICHMENT_PREFIX
from . import utils
from . import constants

SIGHTING_LEVELS = {"0": "Sighting", "1": "False Positive", "2": "Expiration"}

THREAT_LEVELS = {"1": "High", "2": "Medium", "3": "Low", "4": "Undefined"}

DISTRIBUTION_LEVELS = {
    "0": "Your organization only",
    "1": "This community only",
    "2": "Connected communities",
    "3": "All communities",
    "5": "Inherit",
}

ANALYSIS_LEVELS = {"0": "Initial", "1": "Ongoing", "2": "Completed"}


class BaseDataClass:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_csv(self):
        return dict_to_flat(self.raw_data)


class SaveResponse(BaseDataClass):
    def __init__(self, raw_data, is_saved, error_msg, success_msg):
        super(SaveResponse, self).__init__(raw_data)
        self.is_saved = is_saved
        self.error_msg = error_msg
        self.success_msg = success_msg
        self.message = success_msg if success_msg else error_msg


class Event(BaseDataClass):
    def __init__(
        self,
        raw_data,
        id=None,
        published=None,
        event_creator_email=None,
        info=None,
        related_events=None,
        threat_level_id=None,
        publish_timestamp=None,
        attributes=None,
        timestamp=None,
        objects=[],
        galaxies=None,
        tags=None,
        uuid=None,
        org_name=None,
        date=None,
        analysis=None,
        distribution=None,
    ):
        super(Event, self).__init__(raw_data)
        self.id = id
        self.published = published
        self.event_creator_email = event_creator_email
        self.info = info
        self.related_events = related_events or []
        self.tags = tags or []
        self.galaxies = galaxies or []
        self.attributes = attributes or []
        self.threat_level_id = int(threat_level_id) if threat_level_id else 0
        self.publish_timestamp_ms = (
            int(publish_timestamp) * 1000 if publish_timestamp else 0
        )
        self.timestamp_ms = int(timestamp) * 1000 if timestamp else 0
        self.objects = objects
        self.uuid = uuid
        self.org_name = org_name
        self.date = date
        self.analysis = analysis
        self.distribution = distribution

    def __repr__(self):
        return f"<Event ID: {self.id}>"

    def to_csv(self):
        return {
            "Event ID": self.id,
            "Attributes": " ".join([attribute.value for attribute in self.attributes]),
            "Event Creator Email": self.event_creator_email,
            "Info": self.info,
            "Related Events": " ".join([event.id for event in self.related_events]),
            "Threat Level ID": self.threat_level_id,
            "Timestamp": convert_unixtime_to_datetime(
                self.publish_timestamp_ms
            ).strftime(constants.TIME_FORMAT),
        }

    def to_csv_as_related_event(self):
        return {
            "Event ID": self.id,
            "UUID": self.uuid,
            "Org": self.org_name,
            "Date": self.date,
            "Threat Level": THREAT_LEVELS.get(str(self.threat_level_id)),
            "Analysis": ANALYSIS_LEVELS.get(str(self.analysis)),
            "Distribution": DISTRIBUTION_LEVELS.get(str(self.distribution)),
            "Published": self.published,
            "Event Name": self.info,
        }

    def as_alert_info(self, events, environment_common):
        alert_info = AlertInfo()

        events = list(map(dict_to_flat, events))
        events = map(utils.clean_duplicated_keys, events)
        alert_info.events = list(events)

        alert_info.name = f"MISP Event {self.id}"
        alert_info.rule_generator = constants.RULE_GENERATOR
        alert_info.ticket_id = alert_info.display_id = str(uuid.uuid4())
        alert_info.start_time = alert_info.end_time = self.timestamp_ms
        alert_info.priority = self.siemplify_priority
        alert_info.device_vendor = constants.DEFAULT_VENDOR
        alert_info.device_product = constants.DEFAULT_PRODUCT
        alert_info.environment = environment_common.get_environment(
            dict_to_flat(self.raw_data)
        )

        for k, v in self.raw_data.items():
            if k not in [
                "Attribute",
                "Object",
                "ShadowAttribute",
                "RelatedEvent",
                "Galaxy",
            ]:
                alert_info.extensions.update(dict_to_flat({k: v}))

        return alert_info

    def to_enrichment_data(self):
        clean_enrichment_data = {
            k: v for k, v in self._get_enrichment_data().items() if v
        }
        return add_prefix_to_dict(clean_enrichment_data, DATA_ENRICHMENT_PREFIX)

    def _get_enrichment_data(self):
        return self.to_csv_as_related_event()

    @property
    def siemplify_priority(self):
        if self.threat_level_id == 1:
            return 100
        elif self.threat_level_id == 2:
            return 80
        elif self.threat_level_id == 3:
            return 60
        elif self.threat_level_id == 4:
            return 40
        else:
            return -1


class ApiMessage(BaseDataClass):
    def __init__(self, raw_data, message):
        super(ApiMessage, self).__init__(raw_data)
        self.message = message


class Attribute(BaseDataClass):
    def __init__(
        self,
        raw_data,
        uuid=None,
        id=None,
        category=None,
        value=None,
        type=None,
        event_id=None,
        object_id=None,
        first_seen=None,
        last_seen=None,
        timestamp=None,
        comment=None,
        distribution=None,
        to_ids=None,
        **kwargs,
    ):
        super(Attribute, self).__init__(raw_data)
        self.uuid = uuid
        self.id = id
        self.event_id = event_id
        self.object_id = object_id
        self.category = category
        self.value = value
        self.type = type
        self.distribution = distribution
        self.comment = comment
        self.first_seen = first_seen
        self.last_seen = last_seen
        self.to_ids = to_ids
        self.timestamp = int(timestamp) * 1000 if timestamp else 0

    def __repr__(self):
        return f"<Attribute object {self.value}>"

    def as_event(self, event_name, timestamp, device_product=None):
        return {
            self.type: self.value,
            "category": self.category,
            "StartTime": timestamp,
            "EndTime": timestamp,
            "name": event_name,
            "ingestion_time": unix_now(),
            "device_product": device_product or constants.DEFAULT_PRODUCT,
        }

    def to_base_csv(self):
        return super(Attribute, self).to_csv()

    def as_json(self):
        return self.raw_data.get("Attribute")

    def to_csv(self):
        return {
            "ID": self.id,
            "Value": self.value,
            "Comment": self.comment,
            "Type": self.type,
            "Category": self.category,
            "UUID": self.uuid,
            "Distribution": self.distribution,
            "Timestamp": convert_unixtime_to_datetime(self.timestamp).strftime(
                constants.TIME_FORMAT
            ),
        }

    def to_attributes_enrich_csv(self):
        return flat_dict_to_csv(dict_to_flat(self.to_enrich_attributes_table()))

    def to_enrich_attributes_table(self):
        return {
            "ID": self.id,
            "Event ID": self.event_id,
            "IDS": self.to_ids,
            "Type": self.type,
            "Category": self.category,
            "UUID": self.uuid,
            "Distribution": DISTRIBUTION_LEVELS.get(str(self.distribution)),
            "Timestamp": convert_unixtime_to_datetime(self.timestamp).strftime(
                constants.TIME_FORMAT
            ),
        }

    def to_enrichment_data(
        self,
        use_prefix=True,
        method="get_enrichment_data",
        prefix=DATA_ENRICHMENT_PREFIX,
    ):
        clean_enrichment_data = {k: v for k, v in getattr(self, method)().items() if v}
        return (
            add_prefix_to_dict(clean_enrichment_data, prefix)
            if use_prefix
            else clean_enrichment_data
        )

    def get_enrichment_data(self):
        return {self.type: self.value}

    def get_attribute_enrichment_data(self):
        return {
            "ID": self.id,
            "Category": self.category,
            "Type": self.type,
            "UUID": self.uuid,
            "Timestamp": convert_unixtime_to_datetime(self.timestamp).strftime(
                constants.TIME_FORMAT
            ),
            "Distribution": DISTRIBUTION_LEVELS.get(str(self.distribution)),
            "IDS": self.to_ids,
        }


class Tag(BaseDataClass):
    def __init__(self, raw_data, id, name):
        super(Tag, self).__init__(raw_data)
        self.id = id
        self.name = name


class Sighting(BaseDataClass):
    def __init__(
        self,
        raw_data,
        id,
        type,
        date_sighting=None,
        source=None,
        organisation_name=None,
        **kwargs,
    ):
        super(Sighting, self).__init__(raw_data)
        self.id = id
        self.source = source
        self.type = type
        self.date_sighting = date_sighting
        self.organisation_name = organisation_name

    def to_csv(self):
        return {
            "ID": self.id,
            "Date": self.date_sighting,
            "Source": self.source,
            "Type": SIGHTING_LEVELS.get(self.type),
            "Organisation": self.organisation_name,
        }


class MISPObject(BaseDataClass):
    def __init__(
        self,
        raw_data,
        id=None,
        name=None,
        description=None,
        uuid=None,
        event_id=None,
        comment=None,
        timestamp=None,
        attributes=[],
        meta_category=None,
    ):
        super(MISPObject, self).__init__(raw_data)
        self.id = id
        self.name = name
        self.description = description
        self.uuid = uuid
        self.event_id = event_id
        self.comment = comment
        self.meta_category = meta_category
        self.timestamp = timestamp
        self.attributes = attributes

    def to_attributes_csv(self):
        return [attribute.to_base_csv() for attribute in self.attributes]

    def to_object_json(self):
        temp = copy.deepcopy(self.raw_data)
        if "Attribute" in temp:
            del temp["Attribute"]

        return temp

    def to_csv(self):
        return {
            "Object UUID": self.uuid,
            "Name": self.name,
            "Description": self.description,
            "Category": self.meta_category,
            "Comment": self.comment,
        }

    def as_event(self, event_name, timestamp, attributes, device_product=None):
        obj_event = defaultdict(list)

        for attribute in attributes:
            obj_event[attribute.type].append(attribute.value)

        obj_event = dict_to_flat(obj_event)

        obj_event["category"] = self.meta_category
        obj_event["StartTime"] = obj_event["EndTime"] = timestamp
        obj_event["name"] = event_name
        obj_event["device_product"] = device_product or constants.DEFAULT_PRODUCT
        obj_event["ingestion_time"] = unix_now()
        return obj_event


class ObjectTemplate(BaseDataClass):
    def __init__(self, raw_data, id=None, name=None):
        super(ObjectTemplate, self).__init__(raw_data)
        self.id = id
        self.name = name


class Galaxy(BaseDataClass):
    def __init__(self, raw_data, type=None, name=None, **kwargs):
        super(Galaxy, self).__init__(raw_data)
        self.type = type
        self.name = name


class MispAttachment(BaseDataClass):
    def __init__(self, raw_data, filename=None, content=None):
        super(MispAttachment, self).__init__(raw_data)
        self.filename = filename
        self.content = content
