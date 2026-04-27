from __future__ import annotations
from .datamodels import *


class CBResponseParser:
    @staticmethod
    def build_siemplify_binary_obj(binary_json):
        return Binary(binary_json)

    @staticmethod
    def build_siemplify_process_obj(process_json):
        return Process(
            raw_data=process_json,
            hostname=process_json.get("hostname", None),
            segment_id=process_json.get("segment_id", None),
        )

    @staticmethod
    def build_siemplify_elapsed_process(elapsed_process_json):
        process_json = elapsed_process_json.get("process", {})
        file_modes = [
            FileMod(file_mode_json)
            for file_mode_json in process_json.get("filemod_complete", [])
        ]
        process = Process(process_json, file_modes=file_modes)
        return ElapsedProcess(elapsed_process_json, process)

    @staticmethod
    def build_siemplify_process_with_tree_data(tree_data_json):
        return Process(
            tree_data_json,
            # parent=Process(tree_data_json.get("parent", {})),
            parent=CBResponseParser.build_siemplify_process_obj(
                tree_data_json.get("parent", {})
            ),
            siblings=[
                CBResponseParser.build_siemplify_process_obj(sibling)
                for sibling in tree_data_json.get("sibling", [])
            ],
            children=[
                CBResponseParser.build_siemplify_process_obj(child)
                for child in tree_data_json.get("children", [])
            ],
        )

    @staticmethod
    def build_siemplify_sensor_document_obj(sensor_document_json):
        return SensorDocument(
            raw_data=sensor_document_json,
            sensor_document_id=sensor_document_json.get("id", None),
            hostname=sensor_document_json.get("computer_name", None),
            fqdn=sensor_document_json.get("computer_dns_name", None),
            ip_address=sensor_document_json.get("network_adapters", None),
            status=sensor_document_json.get("status", None),
            isolated=sensor_document_json.get("network_isolation_enabled", None),
            operating_system=sensor_document_json.get(
                "os_environment_display_string", None
            ),
            uptime=sensor_document_json.get("sensor_uptime", None),
            health_status=sensor_document_json.get("sensor_health_message", None),
            last_updated=sensor_document_json.get("last_update", None),
            live_response_support=sensor_document_json.get("supports_cblr", None),
            group_id=sensor_document_json.get("group_id", None),
        )

    @staticmethod
    def build_siemplify_alert_obj(alert_json):
        return Alert(
            alert_json,
            unique_id=alert_json.get("unique_id", None),
            created_time=alert_json.get("created_time", 1),
            process_id=alert_json.get("process_id", None),
            segment_id=alert_json.get("segment_id", None),
            md5=alert_json.get("md5", None),
            watchlist_name=alert_json.get("watchlist_name", None),
            observed_filename=alert_json.get("observed_filename", []),
        )
