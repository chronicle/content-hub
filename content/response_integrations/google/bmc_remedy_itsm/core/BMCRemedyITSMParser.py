from __future__ import annotations
from .datamodels import *


class BMCRemedyITSMParser:
    def build_template_objects(self, raw_data):
        return [self.build_template_object(item) for item in raw_data.get("entries")]

    @staticmethod
    def build_template_object(raw_data):
        return Template(
            raw_data=raw_data,
            template_id=raw_data.get("values", {}).get("HPD Template ID", {}),
        )

    def build_incident_objects(self, raw_data):
        return [self.build_incident_object(item) for item in raw_data.get("entries")]

    @staticmethod
    def build_incident_object(raw_data):
        return Incident(
            raw_data=raw_data.get("values", {}),
            request_id=raw_data.get("values", {}).get("Request ID"),
            entry_id=raw_data.get("values", {}).get("Entry ID"),
            status=raw_data.get("values", {}).get("Status"),
        )

    def build_incidents_details_list(self, raw_json):
        return [
            self.build_incident_details(item) for item in raw_json.get("entries", [])
        ]

    @staticmethod
    def build_incident_details(raw_data):
        return IncidentDetails(
            raw_data=raw_data.get("values"),
            inc_number=raw_data.get("values", {}).get("Incident Number"),
        )

    def build_work_notes_list(self, raw_json):
        return [self.build_work_note(item) for item in raw_json.get("entries", [])]

    @staticmethod
    def build_work_note(raw_data):
        return WorkNote(
            raw_data=raw_data.get("values"),
            submitter=raw_data.get("values", {}).get("Submitter"),
            description=raw_data.get("values", {}).get("Detailed Description"),
            submit_date=raw_data.get("values", {}).get("Work Log Submit Date"),
        )

    @staticmethod
    def build_record_details(raw_data):
        return RecordDetails(raw_data=raw_data.get("values"))

    @staticmethod
    def build_record_obj(raw_data):
        raw_data = raw_data.get("values")
        return Record(
            raw_data=raw_data,
            work_log_id=raw_data.get("Work Log ID", ""),
            submitter=raw_data.get("Submitter", ""),
            submit_date=raw_data.get("Submit Date", ""),
            assigned_to=raw_data.get("Assigned To", ""),
            last_modified_by=raw_data.get("Last Modified By", ""),
            last_modified_date=raw_data.get("Last Modified Date", ""),
            status=raw_data.get("Status", ""),
            short_description=raw_data.get("Short Description", ""),
            status_history=raw_data.get("Status History", ""),
            assignee_groups=raw_data.get("Assignee Groups", ""),
        )
