from __future__ import annotations

from .datamodels import *


class ServiceNowParser:
    @staticmethod
    def build_upload_file_object(upload_file_json):
        if not upload_file_json:
            return None

        return UploadFile(raw_data=upload_file_json)

    @staticmethod
    def build_cmdb_record_object(raw_data):
        if not raw_data:
            return None

        record_objects = raw_data.get("result", [])

        return [
            CMDB_Record(
                raw_data=record_detail,
                sys_id=record_detail.get("sys_id"),
                name=record_detail.get("name"),
            )
            for record_detail in record_objects
        ]

    @staticmethod
    def build_cmdb_record_details_object(raw_data):
        if not raw_data:
            return None

        return CMDB_Record_Detail(
            raw_data=raw_data,
            inbound_relations=[
                ServiceNowParser.build_cmdb_record_inbound_object(inbound_relation)
                for inbound_relation in raw_data.get("result", {}).get("inbound_relations", {})
            ],
            outbound_relations=[
                ServiceNowParser.build_cmdb_record_outbound_object(outbound_relation)
                for outbound_relation in raw_data.get("result", {}).get("outbound_relations", {})
            ],
        )

    @staticmethod
    def build_cmdb_record_outbound_object(raw_data):
        if not raw_data:
            return None

        return Outbound_Relation(
            raw_data=raw_data,
            outbound_sys_id=raw_data.get("sys_id"),
            outbound_cmdb_type=raw_data.get("type", {}).get("display_value", {}),
            outbound_target=raw_data.get("target").get("display_value", {}),
        )

    @staticmethod
    def build_cmdb_record_inbound_object(raw_data):
        if not raw_data:
            return None

        return Inbound_Relation(
            raw_data=raw_data,
            inbound_sys_id=raw_data.get("sys_id"),
            inbound_cmdb_type=raw_data.get("type", {}).get("display_value", {}),
            inbound_target=raw_data.get("target").get("display_value", {}),
        )

    def build_attachments_object(self, raw_data, download_folder_path):
        return [
            self.get_attachment(raw_data=attachment_data, download_folder_path=download_folder_path)
            for attachment_data in raw_data.get("result", [])
        ]

    def get_attachment(self, raw_data, download_folder_path=None):
        return Attachment(
            raw_data=raw_data,
            sys_id=raw_data["sys_id"],
            download_link=raw_data.get("download_link", ""),
            download_path=download_folder_path,
            filename=raw_data.get("file_name", ""),
        )

    def build_users_data(self, raw_data):
        return [self.get_user(raw_data=record) for record in raw_data.get("result", [])]

    def get_user(self, raw_data):
        return User(
            raw_data=raw_data,
            sys_id=raw_data.get("sys_id", ""),
            user_name=raw_data.get("user_name", ""),
            name=raw_data.get("name", ""),
            email=raw_data.get("email", ""),
        )

    def build_user_related_records(self, raw_data):
        return [
            self.get_user_related_record(raw_data=record) for record in raw_data.get("result", [])
        ]

    def get_user_related_record(self, raw_data):
        return UserRelatedRecord(
            raw_data=raw_data,
            sys_id=raw_data.get("sys_id", ""),
            short_description=raw_data.get("short_description", ""),
            created_at=raw_data.get("sys_created_on", ""),
        )

    def build_incidents(self, raw_data):
        return [
            self.build_incident_instance(raw_data=incident)
            for incident in raw_data.get("result", [])
        ]

    def build_incident_instance(self, raw_data):
        return Incident(
            raw_data=raw_data,
            child_incidents=raw_data.get("child_incidents", 0),
            sys_id=raw_data.get("sys_id", ""),
            number=raw_data.get("number", ""),
            state=raw_data.get("state", ""),
            closed_at=raw_data.get("closed_at", ""),
            caller_id=self.get_value(raw_data, "caller_id"),
            opener_id=self.get_value(raw_data, "opened_by"),
            sys_created_on=raw_data.get("sys_created_on"),
        )

    def get_value(self, raw_data, key):
        field = raw_data.get(key, "")
        if isinstance(field, str):
            return field
        return field.get("value", "")

    def build_child_incidents(self, raw_data):
        return [
            self.get_child_incident(raw_data=child_incident)
            for child_incident in raw_data.get("result", [])
        ]

    def get_child_incident(self, raw_data):
        return ChildIncident(
            raw_data=raw_data,
            sys_id=raw_data.get("sys_id", ""),
            number=raw_data.get("number", ""),
            short_description=raw_data.get("short_description", ""),
            created_at=raw_data.get("sys_created_on", ""),
        )

    def build_results(self, raw_json, method):
        return [getattr(self, method)(item_json) for item_json in raw_json.get("result", [])]

    def build_result(self, raw_json, method):
        return getattr(self, method)(raw_json.get("result", {}))

    def build_incident(self, item_json):
        return self.build_incident_instance(item_json)

    def build_ticket(self, item_json):
        return Ticket(
            raw_data=item_json,
            state=item_json.get("state", ""),
            sys_id=item_json.get("sys_id", ""),
            number=item_json.get("number", ""),
        )

    def build_record_detail(self, item_json):
        return RecordDetail(raw_data=item_json)

    def build_comment(self, item_json):
        return Comment(
            raw_data=item_json,
            value=item_json.get("value"),
            sys_created_on=item_json.get("sys_created_on"),
            element_id=item_json.get("element_id"),
        )

    def build_object(self, item_json):
        return ServiceNowObject(raw_data=item_json, sys_id=item_json.get("sys_id"))

    def build_comment_objects(self, raw_data):
        return [self.build_comment(item) for item in raw_data.get("result", [])]

    @staticmethod
    def build_affected_ci(raw_data):
        return AffectedCI(
            raw_data=raw_data,
            sys_id=raw_data.get("ci_item", {}).get("value"),
            incident_sys_id=raw_data.get("task", {}).get("value"),
        )

    @staticmethod
    def build_affected_ci_details(raw_data):
        return AffectedCIDetails(raw_data=raw_data, sys_id=raw_data.get("sys_id"))
