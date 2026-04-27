from __future__ import annotations
from .datamodels import *


class CheckpointParser:
    def get_access_layers(self, raw_data):
        return [
            self.get_access_layer(raw_json=layer_json)
            for layer_json in raw_data.get("access-layers", [])
        ]

    def get_threat_layers(self, raw_data):
        return [
            self.get_threat_layer(raw_json=layer_json)
            for layer_json in raw_data.get("threat-layers", [])
        ]

    def get_policies(self, raw_data):
        return [
            self.get_policy(raw_json=package_json)
            for package_json in raw_data.get("packages", [])
        ]

    def get_logs(self, raw_data):
        return [
            self.get_log(raw_json=log_json) for log_json in raw_data.get("logs", [])
        ]

    def get_access_layer(self, raw_json):
        return AccessLayer(
            raw_json=raw_json,
            name=raw_json.get("name"),
            layer_type=raw_json.get("type"),
            shared=raw_json.get("shared"),
            applications_and_url_filtering=raw_json.get(
                "applications-and-url-filtering"
            ),
            content_awareness=raw_json.get("content-awareness"),
            mobile_access=raw_json.get("mobile-access"),
            firewall=raw_json.get("firewall"),
            comments=raw_json.get("comments"),
            creator=raw_json.get("meta-info").get("creator"),
            read_only=raw_json.get("read-only"),
            uid=raw_json.get("uid"),
        )

    def get_threat_layer(self, raw_json):
        return ThreatLayer(
            raw_json=raw_json,
            name=raw_json.get("name"),
            ips_layer=raw_json.get("ips-layer"),
            comments=raw_json.get("comments"),
            creator=raw_json.get("meta-info").get("creator"),
            read_only=raw_json.get("read-only"),
            uid=raw_json.get("uid"),
        )

    def get_policy(self, raw_json):
        return Policy(raw_json=raw_json)

    def get_log(self, raw_json):
        return LogResult(
            raw_json=raw_json,
            log_id=raw_json.get("id"),
            title=raw_json.get("cb_title"),
            severity=raw_json.get("severity"),
            subject=raw_json.get("subject"),
            index_time=raw_json.get("index_time"),
            time=raw_json.get("time"),
        )

    def get_task(self, raw_json, log_id):
        return Task(
            raw_json=raw_json,
            log_id=log_id,
            attachments=self.__get_attachments(raw_json.get("tasks", [])),
        )

    def __get_attachments(self, tasks):
        return [
            self.__get_attachment(attachment)
            for task in tasks
            for details in task.get("task-details", [])
            for attachment in details.get("attachments", [])
        ]

    def __get_attachment(self, attachment):
        return Attachment(
            raw_json=attachment,
            content=attachment.get("base64-data", ""),
            filename=attachment.get("file-name", "file"),
        )
