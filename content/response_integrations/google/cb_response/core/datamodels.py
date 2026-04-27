from __future__ import annotations
from soar_sdk.SiemplifyUtils import dict_to_flat, flat_dict_to_csv, add_prefix_to_dict


class BaseDataClass:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_csv(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Binary(BaseDataClass):
    def __init__(self, raw_data):
        super(Binary, self).__init__(raw_data)


class ElapsedProcess(BaseDataClass):
    def __init__(self, raw_data, process=None):
        super(ElapsedProcess, self).__init__(raw_data)
        self.process = process if process else Process({})


class Process(BaseDataClass):
    def __init__(
        self,
        raw_data,
        file_modes=None,
        parent=None,
        siblings=None,
        children=None,
        hostname=None,
        segment_id=None,
    ):
        super(Process, self).__init__(raw_data)
        self.hostname = hostname
        self.segment_id = segment_id
        self.file_modes = file_modes if file_modes else []
        self.parent = parent
        self.siblings = siblings if siblings else []
        self.children = children if children else []

    def is_hostname_equal(self, hostname):
        return self.hostname == hostname


class FileMod(BaseDataClass):
    def __init__(self, raw_data):
        super(FileMod, self).__init__(raw_data)

    def to_data_table(self):
        header = [
            "operation type",
            "event time",
            "file path",
            "md5",
            "file type",
            "is potential tamper",
        ]
        data = self.raw_data.split("|")
        return dict(list(zip(header, data)))


class SensorDocument(BaseDataClass):
    def __init__(
        self,
        raw_data,
        sensor_document_id,
        hostname,
        fqdn,
        ip_address,
        status,
        isolated,
        operating_system,
        uptime,
        health_status,
        last_updated,
        live_response_support,
        group_id,
    ):
        super(SensorDocument, self).__init__(raw_data)
        self.sensor_document_id = sensor_document_id
        self.hostname = hostname
        self.fqdn = fqdn
        self.ip_address = ip_address
        self.status = status
        self.isolated = isolated
        self.operating_system = operating_system
        self.uptime = uptime
        self.health_status = health_status
        self.last_updated = last_updated
        self.live_response_support = live_response_support
        self.group_id = group_id

    def to_csv(self, prefix=None):
        return flat_dict_to_csv(
            {
                "Id": self.sensor_document_id,
                "Hostname": self.hostname,
                "FQDN": self.fqdn,
                "Ip Address": self.ip_address,
                "Status": self.status,
                "Isolated": self.isolated,
                "Operating System": self.operating_system,
                "Uptime": self.uptime,
                "Health Status": self.health_status,
                "Last Updated": self.last_updated,
                "Live Response Support": self.live_response_support,
            }
        )

    def to_enrichment_data(self, prefix):
        return add_prefix_to_dict(dict_to_flat(self.raw_data), prefix)


class Alert(BaseDataClass):
    def __init__(
        self,
        raw_data,
        unique_id,
        created_time=None,
        process_id=None,
        segment_id=None,
        md5=None,
        watchlist_name=None,
        observed_filename=[],
    ):
        super(Alert, self).__init__(raw_data)
        self.unique_id = unique_id
        self.created_time = created_time if created_time else 1
        self.end_time = None
        self.process_id = process_id
        self.segment_id = segment_id
        self.md5 = md5
        self.observed_filename = observed_filename
        self.watchlist_name = watchlist_name
        self.process_segment_id = None
        self.process_alert_link = None
        self.alert_link = None

    def as_event(self):
        event = self.raw_data
        event.update(
            {
                "alert_link": self.alert_link,
                "process_segment_id": self.process_segment_id,
                "process_alert_link": self.process_alert_link,
            }
        )
        return dict_to_flat(event)

    def get_from_raw_json(self, key, default_value=None):
        return self.raw_data.get(key, default_value)
