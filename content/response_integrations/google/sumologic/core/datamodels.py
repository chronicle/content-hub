from __future__ import annotations
import copy
import json
import uuid

from TIPCommon import dict_to_flat

from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from .consts import COMPLETED_STATUS, ERROR_STATUSES, DEFAULT_VENDOR, DEFAULT_PRODUCT


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def as_json(self):
        return self.raw_data


class JobInfo(BaseModel):
    """
    Search Job Info data model
    """

    def __init__(self, raw_data, state=None, message_count=None):
        super(JobInfo, self).__init__(raw_data)
        self.state = state
        self.message_count = message_count

    @property
    def completed(self):
        return bool(self.state == COMPLETED_STATUS)

    @property
    def failed(self):
        return bool(self.state in ERROR_STATUSES)


class SearchMessage(BaseModel):
    """
    Search Record data model
    """

    def __init__(
        self,
        raw_data,
        message_time=None,
        block_id=None,
        raw=None,
        source_id=None,
        collector=None,
        message_id=None,
        message_count=None,
        receipt_time=None,
        source=None,
        source_category=None,
    ):
        super(SearchMessage, self).__init__(raw_data)
        self.message_time = message_time
        self.block_id = block_id
        self.raw = raw
        self.source_id = source_id
        self.collector = collector
        self.message_id = message_id
        self.message_count = message_count
        self.receipt_time = receipt_time
        self.source = source
        self.source_category = source_category

        try:
            self.receipt_time = int(self.receipt_time)
        except:
            pass

        try:
            self.message_time = int(self.message_time)
        except:
            pass

    def as_json(self):
        raw_data = copy.deepcopy(self.raw_data)
        try:
            raw_data["_raw"] = json.loads(raw_data.get("_raw", {}))
        except:
            pass
        return raw_data

    def as_csv(self):
        raw_data = copy.deepcopy(self.raw_data)
        return dict_to_flat(raw_data)

    def as_event(self):
        raw_data = copy.deepcopy(self.raw_data)
        try:
            raw_data["_raw"] = json.loads(raw_data.get("_raw", {}))
        except:
            pass
        return dict_to_flat(raw_data)

    def get_alert_info(
        self,
        timestamp_field_name,
        device_product_field_name,
        alert_name_field,
        environment_common,
    ) -> AlertInfo:
        alert_info = AlertInfo()

        event = self.as_event()

        alert_time = event.get(timestamp_field_name, 1)
        alert_info.start_time = alert_time
        alert_info.end_time = alert_time
        alert_info.rule_generator = self.source_category
        alert_info.device_product = (
            event.get(device_product_field_name) or DEFAULT_PRODUCT
        )
        alert_info.name = event.get(alert_name_field)
        alert_info.environment = environment_common.get_environment(event)
        alert_info.device_vendor = DEFAULT_VENDOR
        alert_info.ticket_id = self.message_id
        alert_info.display_id = str(uuid.uuid4())
        alert_info.events = [event]
        return alert_info
