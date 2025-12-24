from __future__ import annotations

import copy
import uuid
from collections import defaultdict

from constants import (
    AI_DEVICE_PRODUCT,
    AI_DEVICE_VENDOR,
    DARKTRACE_AI_EVENT,
    DEVICE_PRODUCT,
    DEVICE_VENDOR,
    EVENT_TYPES_NAMES,
    MIN_PRIORITY,
    SEVERITY_MAP,
)
from TIPCommon.transformation import add_prefix_to_dict, dict_to_flat
from TIPCommon.types import SingleJson


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


class AiAlert(BaseModel):
    def __init__(
        self,
        raw_data: dict,
        alert_id: str,
        name: str,
        description: str,
        score: float,
        time: int,
        source_grouping_identifier: str,
        start_time: int,
        end_time: int,
    ):
        super(AiAlert, self).__init__(raw_data)
        self.uuid = uuid.uuid4()
        self.id = alert_id
        self.name = name
        self.description = description
        self.score = score
        self.time = time
        self.end_time = end_time
        self.source_grouping_identifier = source_grouping_identifier
        self.start_time = start_time
        self.events = []

    def get_alert_info(self, alert_info, environment_common, device_product_field):
        alert_info.environment = environment_common.get_environment(self.raw_data)
        alert_info.ticket_id = self.id
        alert_info.display_id = f"{DARKTRACE_AI_EVENT}: {self.id}"
        alert_info.name = self.name
        alert_info.description = self.description
        alert_info.device_vendor = AI_DEVICE_VENDOR
        alert_info.device_product = self.raw_data.get(device_product_field) or AI_DEVICE_PRODUCT
        alert_info.priority = self.get_siemplify_severity(self.score)
        alert_info.rule_generator = self.name
        alert_info.start_time = self.start_time
        alert_info.source_grouping_identifier = self.source_grouping_identifier
        alert_info.end_time = self.end_time
        alert_info.events = self.to_events()
        alert_info.creation_time_unix_time_ms = self.time

        return alert_info

    @staticmethod
    def get_siemplify_severity(score: float) -> int:
        """Get the severity score with mapping

        Args:
            score: severity score.

        Returns:
            int: The value of the severity.
        """
        rounded_score = round(score)

        for threshold in SEVERITY_MAP.values():
            if threshold >= rounded_score:
                return threshold

        return SEVERITY_MAP["INFO"]

    def flatten_data(self, data: list[list[SingleJson]]) -> list[SingleJson]:
        """Flattens a hierarchical data structure into a list of flat dicts.

        Each item in the output list represents a flattened version of the
        content blocks contained within the input data.
        The method handles special cases, such as integer and string lists,
        and also formats time-related data distinctively.

        Args:
            data (list[list[SingleJson]]):
                A nested list of dictionaries, where each dict represents a
                content block with a header, key, type, and values

        Returns:
            list[SingleJson]:
                A list of flattened dictionaries, each representing a single
                content block, with unique and combined fields from the
                original structure

        Notes:
            - The input data is expected to be a list of lists, where each inner
            list contains dicts with keys like 'header', 'key', 'type', and
            'values'

            - Each 'values' key should contain a list, where elements can be
            strings, integers, or dictionaries

            - Time-related data is specially processed and integrated into the
            output dictionaries

            - The method ensures that the output list contains unique
            dictionaries, removing any duplicates

            - If a content block does not contain time-related data, a default
            'createdAt' field is added using the class's 'time' attribute

        Example:
            >>> input_data = [
            ...     [
            ...         {
            ...             "header": "Header1",
            ...             "contents": [
            ...                 {"key": "Key1", "values": ["value1", "value2"]},
            ...                 {
            ...                     "key": "Key2",
            ...                     "values": [{"SubKey1": "subvalue1", "SubKey2": "subvalue2"}],
            ...                 },
            ...             ],
            ...         }
            ...     ]
            ... ]
            >>>
            >>> flatten_data(input_data)
            [
                {
                    "header": "Header1",
                    "Key1": "value1",
                    "Key2_SubKey1": "subvalue1",
                    "Key2_SubKey2": "subvalue2",
                    "data_type": "Event",
                    "createdAt": "1699693989000"
                },
                {
                    "header": "Header1",
                    "Key1": "value2",
                    "Key2_SubKey1": "subvalue1",
                    "Key2_SubKey2": "subvalue2",
                    "data_type": "Event",
                    "createdAt": "1699693989000"
                }
            ]

        """
        output = []

        for section in data:
            for content_block in section:
                header = content_block["header"]
                contents = content_block["contents"]

                # Base structure for output items
                base_structure = {"header": header}

                # Handle keys with a list of strings as values
                for content in contents:
                    # Check if the first value is a string or int
                    if isinstance(content["values"][0], int):
                        content["values"] = [", ".join(map(str, content["values"]))]
                    if isinstance(content["values"][0], str):
                        content["values"] = [", ".join(content["values"])]

                # Special handling for Time key
                time_value = defaultdict(list)
                for content in contents:
                    if content["key"] == "Time":
                        for value in content["values"]:
                            if isinstance(value, dict):
                                for sub_key, sub_value in value.items():
                                    time_value[sub_key].append(sub_value)
                            if isinstance(value, int):
                                base_structure.update({"Time": value})
                base_structure.update({
                    f"Time.{k}": v[0] if len(v) == 1 else v for k, v in time_value.items()
                })

                for content in contents:
                    if content["key"] != "Time":
                        key = content["key"] if content["key"] is not None else content["type"]
                        for value in content["values"]:
                            flattened_item = base_structure.copy()

                            # Iterate over the rest of the contents to include all details
                            for inner_content in contents:
                                inner_key = (
                                    inner_content["key"]
                                    if inner_content["key"] is not None
                                    else inner_content["type"]
                                )

                                # Skip processing Time key as it's already been handled
                                if inner_key != "Time":
                                    if inner_key == key:
                                        if isinstance(value, dict):
                                            for sub_key, sub_val in value.items():
                                                flattened_key = f"{inner_key}_{sub_key}".replace(
                                                    " ", "_"
                                                )
                                                flattened_item[flattened_key] = sub_val
                                        else:
                                            flattened_key = inner_key.replace(" ", "_")
                                            flattened_item[flattened_key] = value
                                    else:
                                        if isinstance(inner_content["values"][0], dict):
                                            for sub_key, sub_val in inner_content["values"][
                                                0
                                            ].items():
                                                flattened_key = f"{inner_key}_{sub_key}".replace(
                                                    " ", "_"
                                                )
                                                flattened_item[flattened_key] = sub_val
                                        else:
                                            flattened_key = inner_key.replace(" ", "_")
                                            flattened_item[flattened_key] = inner_content["values"][
                                                0
                                            ]
                            flattened_item["data_type"] = "Event"
                            output.append(flattened_item)

        # Remove duplicates
        seen_records = set()
        unique_output = []
        for record in output:
            record_tuple = tuple(
                sorted((k, tuple(v) if isinstance(v, list) else v) for k, v in record.items())
            )
            if record_tuple not in seen_records:
                seen_records.add(record_tuple)
                unique_output.append(record)

        for record in unique_output:
            if not any(k.startswith("Time.") for k in record.keys()):
                record["createdAt"] = self.time

        return unique_output

    def to_events(self):
        events = [self.get_original_event()]
        events.extend([dict_to_flat(event.to_json()) for event in self.events])
        original_event1 = copy.deepcopy(self.to_json())
        details = original_event1.get("details")
        events_pair = self.flatten_data(details)
        for event in events_pair:
            events.extend([dict_to_flat(event)])
        return events

    def get_original_event(self):
        original_event = copy.deepcopy(self.to_json())
        original_event.pop("details", None)
        original_event["data_type"] = "Incident"
        return dict_to_flat(original_event)


class Alert(BaseModel):
    def __init__(self, raw_data, id, name, description, score, time):
        super(Alert, self).__init__(raw_data)
        self.uuid = uuid.uuid4()
        self.id = id
        self.name = name
        self.description = description
        self.score = score
        self.time = time
        self.events = []

    def get_alert_info(self, alert_info, environment_common, device_product_field):
        alert_info.environment = environment_common.get_environment(self.raw_data)
        alert_info.ticket_id = self.id
        alert_info.display_id = str(self.uuid)
        alert_info.name = self.name
        alert_info.description = self.description
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = self.raw_data.get(device_product_field) or DEVICE_PRODUCT
        alert_info.priority = self.get_siemplify_severity()
        alert_info.rule_generator = self.name
        alert_info.start_time = self.time
        alert_info.end_time = self.time
        alert_info.events = self.to_events()

        return alert_info

    def get_siemplify_severity(self):
        rounded_score = self.score * 100

        if 0 <= rounded_score <= SEVERITY_MAP["LOW"]:
            return SEVERITY_MAP["LOW"]
        elif SEVERITY_MAP["LOW"] < rounded_score <= SEVERITY_MAP["MEDIUM"]:
            return SEVERITY_MAP["MEDIUM"]
        elif SEVERITY_MAP["MEDIUM"] < rounded_score <= SEVERITY_MAP["HIGH"]:
            return SEVERITY_MAP["HIGH"]
        elif SEVERITY_MAP["HIGH"] < rounded_score <= SEVERITY_MAP["CRITICAL"]:
            return SEVERITY_MAP["CRITICAL"]

        return SEVERITY_MAP["INFO"]

    def set_events(self, events):
        self.events = events

    def to_events(self):
        events = [self.get_original_event()]
        events.extend([dict_to_flat(event.to_json()) for event in self.events])
        return events

    def get_original_event(self):
        original_event = self.to_json()
        original_event.pop("triggeredComponents")
        original_event["eventType"] = "modelbreach"
        return dict_to_flat(original_event)

    @property
    def priority(self) -> int:
        """Get the priority of the model breach.

        Returns:
            int: The priority of the model breach.
        """
        model = self.raw_data.get("model", {})
        now = model.get("now", {})

        return now.get("priority", MIN_PRIORITY)


class Device(BaseModel):
    def __init__(
        self,
        raw_data,
        mac_address,
        id,
        ip,
        did,
        os,
        hostname,
        type_label,
        device_label,
        typename,
        first_seen,
        last_seen,
    ):
        super(Device, self).__init__(raw_data)
        self.mac_address = mac_address
        self.id = id
        self.ip = ip
        self.did = did
        self.os = os
        self.hostname = hostname
        self.type_label = type_label
        self.device_label = device_label
        self.typename = typename
        self.first_seen = first_seen
        self.last_seen = last_seen

    def to_table(self):
        table_data = {
            "macaddress": self.mac_address,
            "id": self.id,
            "ip": self.ip,
            "did": self.did,
            "os": self.os,
            "hostname": self.hostname,
            "typelabel": self.type_label,
            "devicelabel": self.device_label,
        }

        return {key: value for key, value in table_data.items() if value}

    def to_similars_table(self):
        table_data = {
            "IP Address": self.ip,
            "Mac Address": self.mac_address,
            "OS": self.os,
            "Hostname": self.hostname,
            "Type": self.typename,
            "First Seen": self.first_seen,
            "Last Seen": self.last_seen,
        }

        return {key: value for key, value in table_data.items() if value}

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.to_table())
        return add_prefix_to_dict(data, prefix) if prefix else data

    def as_insight(self, identifier):
        return (
            f"<p><strong>Endpoint: </strong>{identifier}</p>"
            f"<table><tbody>"
            f"<tr><td><strong>Hostname:</strong></td><td>{self.hostname}</td></tr>"
            f"<tr><td><strong>IP Address:</strong></td><td>{self.ip}</td></tr>"
            f"<tr><td><strong>Mac Address:</strong></td><td>{self.mac_address}</td></tr>"
            f"<tr><td><strong>OS:</strong></td><td>{self.os}</td></tr>"
            f"<tr><td><strong>Type:</strong></td><td>{self.type_label}</td></tr>"
            f"<tr><td><strong>Label:</strong></td><td>{self.device_label}</td></tr>"
            f"</tbody></table>"
        )


class EndpointDetails(BaseModel):
    def __init__(
        self,
        raw_data,
        ip,
        country,
        asn,
        city,
        region,
        hostname,
        name,
        longitude,
        latitude,
        devices,
        ips,
        locations,
    ):
        super(EndpointDetails, self).__init__(raw_data)
        self.ip = ip
        self.country = country
        self.asn = asn
        self.city = city
        self.region = region
        self.hostname = hostname
        self.name = name
        self.longitude = longitude
        self.latitude = latitude
        self.devices = devices
        self.ips = ips
        self.locations = locations

    def to_table(self):
        table_data = {
            "ip": self.ip,
            "country": self.country,
            "asn": self.asn,
            "city": self.city,
            "region": self.region,
            "hostname": self.hostname,
            "name": self.name,
            "longitude": self.longitude,
            "latitude": self.latitude,
            "count_related_devices": len(self.devices),
            "associated_ips": ",".join([ip.get("ip") for ip in self.ips]),
            "associated_countries": ",".join([
                location.get("country") for location in self.locations
            ]),
        }

        return {key: value for key, value in table_data.items() if value}

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.to_table())
        return add_prefix_to_dict(data, prefix) if prefix else data

    def to_csv(self):
        return [
            {
                "MacAddress": device.get("macaddress"),
                "Vendor": device.get("vendor"),
                "IP": device.get("ip"),
                "Hostname": device.get("hostname"),
                "OS": device.get("os"),
                "Type": device.get("typelabel"),
            }
            for device in self.devices
        ]


class ModelBreach(BaseModel):
    def __init__(self, raw_data, acknowledged):
        super(ModelBreach, self).__init__(raw_data)
        self.acknowledged = acknowledged


class Event(BaseModel):
    def __init__(self, raw_data):
        super(Event, self).__init__(raw_data)

    def to_table(self, event_type):
        if (
            event_type == EVENT_TYPES_NAMES["connection"]
            or event_type == EVENT_TYPES_NAMES["unusualconnection"]
            or event_type == EVENT_TYPES_NAMES["newconnection"]
        ):
            table_data = {
                "Direction": self.raw_data.get("direction"),
                "Source Port": self.raw_data.get("sourcePort"),
                "Destination Port": self.raw_data.get("destinationPort"),
                "Protocol": self.raw_data.get("protocol"),
                "Application": self.raw_data.get("applicationprotocol"),
                "Time": self.raw_data.get("time"),
                "Destination": self.raw_data.get("destination"),
                "Status": self.raw_data.get("status"),
            }

            if (
                event_type == EVENT_TYPES_NAMES["unusualconnection"]
                or event_type == EVENT_TYPES_NAMES["newconnection"]
            ):
                table_data["Info"] = self.raw_data.get("info")

            return table_data

        if event_type == EVENT_TYPES_NAMES["notice"]:
            return {
                "Direction": self.raw_data.get("direction"),
                "Destination Port": self.raw_data.get("destinationPort"),
                "Type": self.raw_data.get("type"),
                "Time": self.raw_data.get("time"),
                "Destination": self.raw_data.get("destination"),
                "Message": self.raw_data.get("msg"),
            }

        if event_type == EVENT_TYPES_NAMES["devicehistory"]:
            return {
                "Name": self.raw_data.get("name"),
                "Value": self.raw_data.get("value"),
                "Reason": self.raw_data.get("reason"),
                "Time": self.raw_data.get("time"),
            }

        if event_type == EVENT_TYPES_NAMES["modelbreach"]:
            return {
                "Name": self.raw_data.get("name"),
                "State": self.raw_data.get("state"),
                "Score": self.raw_data.get("score"),
                "Time": self.raw_data.get("time"),
                "Active": self.raw_data.get("active"),
            }


class ConnectionData(BaseModel):
    def __init__(self, raw_data):
        super(ConnectionData, self).__init__(raw_data)

    def to_json(self):
        data = copy.deepcopy(self.raw_data)

        for item in data.get("deviceInfo", []):
            item.pop("graphData", None)
            item.get("info", {}).pop("externalASNs", None)

        return data

    def to_table(self):
        rows = []
        external_domains = []

        for item in self.raw_data.get("deviceInfo", []):
            external_domains.extend(item.get("info", {}).get("externalDomains", []))

        rows.extend([
            {"Type": "External Domain", "Domain": external_domain.get("domain")}
            for external_domain in external_domains
        ])

        rows.extend([
            {
                "Type": "Internal Device",
                "IP Address": device.get("ip"),
                "Mac Address": device.get("macaddress"),
            }
            for device in self.raw_data.get("devices", [])
        ])

        return rows


class SearchResult(BaseModel):
    def __init__(self, raw_data):
        super(SearchResult, self).__init__(raw_data)
