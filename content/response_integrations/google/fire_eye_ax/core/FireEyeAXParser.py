from __future__ import annotations
from .datamodels import *


class FireEyeAXParser:
    @staticmethod
    def build_submission_object(raw_data):
        response = raw_data.get("entity", {}).get("response", [])
        result_response = raw_data.get("response", [])
        return Submission(
            raw_data=raw_data,
            id=response[0].get("id") if response else "",
            status=raw_data.get("status"),
            result_id=result_response[0].get("id") if result_response else "",
        )

    @staticmethod
    def build_file_submission_object(raw_data):
        return Submission(
            raw_data=raw_data,
            id=raw_data[0].get("ID") if raw_data else "",
            status=None,
            result_id=None,
        )

    @staticmethod
    def build_submission_result_object(raw_data):
        alert = raw_data.get("alert", [])
        if alert:
            os_changes = alert[0].get("explanation", {}).get("osChanges", [])
            cnc_services = alert[0].get("explanation", {}).get("cncServices", {})
            return SubmissionResult(
                raw_data=raw_data,
                malicious=False if alert[0].get("malicious") == "no" else True,
                severity=alert[0].get("severity"),
                process=(
                    alert[0]
                    .get("explanation", {})
                    .get("osChanges", [])[0]
                    .get("process", [])
                    if os_changes
                    else []
                ),
                cnc_service=(
                    alert[0]
                    .get("explanation", {})
                    .get("cncServices", {})
                    .get("cncService", [])
                    if cnc_services
                    else []
                ),
                regkey=(
                    alert[0]
                    .get("explanation", {})
                    .get("osChanges", [])[0]
                    .get("regkey", [])
                    if os_changes
                    else []
                ),
                file_extracted=(
                    alert[0]
                    .get("explanation", {})
                    .get("osChanges", [])[0]
                    .get("file_extracted", [])
                    if os_changes
                    else []
                ),
            )
