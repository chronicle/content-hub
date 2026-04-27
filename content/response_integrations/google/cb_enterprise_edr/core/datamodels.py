from __future__ import annotations
from TIPCommon import dict_to_flat, add_prefix_to_dict_keys


ENRICHMENT_PREFIX = "CB_ENT_EDR"


class Process:
    def __init__(
        self,
        raw_data,
        event_id=None,
        enriched_event_type=None,
        process_name=None,
        process_guid=None,
        process_pid=None,
        parent_guid=None,
        parent_pid=None,
        process_hash=None,
        process_username=None,
        device_timestamp=None,
        event_description=None,
        netconn_protocol=None,
        netconn_port=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.event_id = event_id
        self.enriched_event_type = enriched_event_type
        self.process_name = process_name
        self.process_guid = process_guid
        self.process_pid = process_pid
        self.parent_guid = parent_guid
        self.parent_pid = parent_pid
        self.process_hash = process_hash
        self.process_username = process_username
        self.device_timestamp = device_timestamp
        self.event_description = event_description
        self.netconn_protocol = netconn_protocol
        self.netconn_port = netconn_port

    def to_csv(self):
        return dict_to_flat(
            {
                "Event id": self.event_id,
                "Event Type": self.enriched_event_type,
                "Process Name": self.process_name,
                "Process GUID": self.process_guid,
                "Process PID": (
                    ", ".join([str(pid) for pid in self.process_pid])
                    if isinstance(self.process_pid, list)
                    else self.process_pid
                ),
                "Process Parent GUID": self.parent_guid,
                "Process Parent PID": self.parent_pid,
                "Process File Hash": (
                    ", ".join([str(hash) for hash in self.process_hash])
                    if isinstance(self.process_hash, list)
                    else self.process_hash
                ),
                "Process Run As": (
                    ", ".join(self.process_username)
                    if isinstance(self.process_username, list)
                    else self.process_username
                ),
                "Created Time": self.device_timestamp,
                "Event Description": self.event_description,
                "Netconn Protocol": self.netconn_protocol,
                "Netconn Port": self.netconn_port,
            }
        )


class Event:
    def __init__(self, raw_data, **kwargs):
        self.raw_data = raw_data

    def to_csv(self):
        return dict_to_flat(self.raw_data)


class FileHashMetadata:
    def __init__(
        self,
        raw_data,
        sha256=None,
        md5=None,
        architecture=None,
        available_file_size=None,
        charset_id=None,
        comments=None,
        company_name=None,
        copyright=None,
        file_available=None,
        file_description=None,
        file_size=None,
        file_version=None,
        internal_name=None,
        lang_id=None,
        original_filename=None,
        os_type=None,
        private_build=None,
        product_description=None,
        product_name=None,
        product_version=None,
        special_build=None,
        trademark=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.sha256 = sha256
        self.md5 = md5
        self.architecture = architecture
        self.available_file_size = available_file_size
        self.charset_id = charset_id
        self.comments = comments
        self.company_name = company_name
        self.copyright = copyright
        self.file_available = file_available
        self.file_description = file_description
        self.file_size = file_size
        self.file_version = file_version
        self.internal_name = internal_name
        self.lang_id = lang_id
        self.original_filename = original_filename
        self.os_type = os_type
        self.private_build = private_build
        self.product_description = product_description
        self.product_name = product_name
        self.product_version = product_version
        self.special_build = special_build
        self.trademark = trademark

    def as_enrichment_data(self):
        enrichment_data = {
            "comments": self.comments,
            "lang_id": self.lang_id,
            "private_build": self.private_build,
            "product_description": self.product_description,
            "special_build": self.special_build,
            "trademark": self.trademark,
        }

        # Clear out None values
        enrichment_data = {
            k: v for k, v in list(enrichment_data.items()) if v is not None
        }

        enrichment_data.update(
            {
                "sha256": self.sha256,
                "md5": self.md5,
                "architecture": self.architecture,
                "available_file_size": self.available_file_size,
                "charset_id": self.charset_id,
                "company_name": self.company_name,
                "copyright": self.copyright,
                "file_available": self.file_available,
                "file_description": self.file_description,
                "file_size": self.file_size,
                "file_version": self.file_version,
                "internal_name": self.internal_name,
                "original_filename": self.original_filename,
                "os_type": self.os_type,
                "product_name": self.product_name,
                "product_version": self.product_version,
            }
        )

        return add_prefix_to_dict_keys(dict_to_flat(enrichment_data), ENRICHMENT_PREFIX)


class FileHashSummary:
    def __init__(
        self,
        raw_data,
        num_devices=None,
        first_seen_device_timestamp=None,
        first_seen_device_id=None,
        first_seen_device_name=None,
        last_seen_device_timestamp=None,
        last_seen_device_id=None,
        last_seen_device_name=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.num_devices = num_devices
        self.first_seen_device_timestamp = first_seen_device_timestamp
        self.first_seen_device_id = first_seen_device_id
        self.first_seen_device_name = first_seen_device_name
        self.last_seen_device_timestamp = last_seen_device_timestamp
        self.last_seen_device_id = last_seen_device_id
        self.last_seen_device_name = last_seen_device_name

    def as_enrichment_data(self):
        enrichment_data = {
            "found_times": self.num_devices,
            "first_seen_device_timestamp": self.first_seen_device_timestamp,
            "first_seen_device_id": self.first_seen_device_id,
            "first_seen_device_name": self.first_seen_device_name,
            "last_seen_device_timestamp": self.last_seen_device_timestamp,
            "last_seen_device_id": self.last_seen_device_id,
            "last_seen_device_name": self.last_seen_device_name,
        }

        return add_prefix_to_dict_keys(dict_to_flat(enrichment_data), ENRICHMENT_PREFIX)
