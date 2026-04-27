from __future__ import annotations
import uuid
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from TIPCommon import dict_to_flat, add_prefix_to_dict
from .constants import DEVICE_VENDOR, DEVICE_PRODUCT, SEVERITY_MAP


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

    def to_table(self):
        table_data_list = []

        for key, value in list(self.raw_data.items()):
            if value is not None and value != "":
                table_data_list.append({"Key": key, "Value": value})

        return table_data_list


class Record(BaseModel):
    def __init__(self, raw_data):
        super(Record, self).__init__(raw_data)


class Query(BaseModel):
    def __init__(self, raw_data, records, total_size):
        super(Query, self).__init__(raw_data)
        self.records = records
        self.total_size = total_size

    def to_json(self):
        return self.records

    def to_table(self):
        table_data = []
        for record in self.records:
            table_data_dict = {}
            for key, value in list(record.items()):
                if value is not None and value != "":
                    table_data_dict[key] = value
            table_data.append(table_data_dict)

        return table_data


class Record_Types(BaseModel):
    def __init__(self, raw_data, name, label, custom):
        super(Record_Types, self).__init__(raw_data)
        self.name = name
        self.label = label
        self.custom = custom

    def to_table(self):
        return {"Name": self.name, "Label": self.label, "Custom": self.custom}


class Incident(BaseModel):
    def __init__(
        self, raw_data, id, title, description, priority, queue_name, created_date
    ):
        super(Incident, self).__init__(raw_data)
        self.id = id
        self.title = title
        self.description = description
        self.priority = priority
        self.queue_name = queue_name
        self.created_date = created_date

    def get_alert_info(self, alert_info, environment_common, device_product_field):
        alert_info.environment = environment_common.get_environment(self.raw_data)
        alert_info.ticket_id = self.id
        alert_info.display_id = str(uuid.uuid4())
        alert_info.name = self.title
        alert_info.description = self.description
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = (
            self.raw_data.get(device_product_field) or DEVICE_PRODUCT
        )
        alert_info.priority = self.get_severity()
        alert_info.rule_generator = self.queue_name
        alert_info.start_time = alert_info.end_time = convert_string_to_unix_time(
            self.created_date
        )
        alert_info.events = [self.to_event()]

        return alert_info

    def get_severity(self):
        return SEVERITY_MAP.get(self.priority, -1)

    def to_event(self):
        return dict_to_flat(self.raw_data)
