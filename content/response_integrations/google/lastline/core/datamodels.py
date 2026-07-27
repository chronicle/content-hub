# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
from typing import Dict, List
from .consts import FILE, INTEGRATION_NAME, URL
from TIPCommon import add_prefix_to_dict, dict_to_flat


class SubmissionTask:
    """
    SubmissionTask Data Model
    """

    def __init__(self, raw_data, data, success: int = None):
        self.raw_data = raw_data
        self.success = success
        self.data = data

    def as_json(self) -> Dict:
        return {"success": self.success, "data": self.data.as_json()}

    def as_csv(self):
        return self.data.as_csv()

    def as_insight(self, entity_identifier: str, entity_type: str):
        return self.data.as_insight(entity_identifier, entity_type)

    def as_table(self, entity_type: str, is_enrichment=False):
        if not is_enrichment:
            return self.data.as_csv()
        flat_dict = dict_to_flat(self.data.as_table(entity_type))
        enrichment_data = add_prefix_to_dict(flat_dict, f"{INTEGRATION_NAME}")
        return enrichment_data if is_enrichment else self.data.as_table(entity_type)


class SubmissionTaskData:
    """
    SubmissionTaskData Data Model
    """

    def __init__(
        self,
        raw_data,
        submission: str = None,
        expires: str = None,
        task_uuid: str = None,
        score: int = None,
        malicious_activity=None,
        md5: str = None,
        sha1: str = None,
        sha256: str = None,
        mime_type: str = None,
        analysis_subject=None,
    ):
        self.raw_data = raw_data
        self.submission = submission
        self.expires = expires
        self.task_uuid = task_uuid
        self.score = score
        self.malicious_activity = malicious_activity
        self.analysis_subject = analysis_subject
        self.md5 = md5
        self.sha1 = sha1
        self.sha256 = sha256
        self.mime_type = mime_type

    def as_json(self) -> Dict:
        return self.raw_data

    def as_csv(self) -> Dict:
        malicious_activity_str = ",".join(self.malicious_activity)
        csv_dict = {
            "Submission_Timestamp": self.submission,
            "Latest_Submission_Timestamp": self.raw_data.get(
                "last_submission_timestamp"
            )
            or "",
            "Results_Expiry_Timestamp": self.expires,
            "Analysis_Task_UUID": self.task_uuid,
            "Score": self.score,
            "Malicious_Activity": malicious_activity_str,
        }

        if self.analysis_subject and self.analysis_subject.sha1:
            csv_dict.update(self.analysis_subject.as_csv())

        return csv_dict

    def as_insight(self, entity_identifier, entity_type: str):
        malicious_activity_str = ",\n".join(self.malicious_activity)
        return f"""
            Entity: {entity_identifier}
            Score: {self.raw_data.get('score') if not None else ''}
            Malicious Activity Observed:\n {f"{malicious_activity_str}" or 'N/A'}
            """

    def as_table(self, entity_type: str = URL) -> Dict:
        csv_dict = {
            "Submission_Timestamp": self.submission,
            "Latest_Submission_Timestamp": self.raw_data.get(
                "last_submission_timestamp"
            )
            or "",
            "Results_Expiry_Timestamp": self.expires,
            "Analysis_Task_UUID": self.task_uuid,
            "Score": self.score,
            "Malicious_Activity": self.malicious_activity,
        }

        if entity_type == FILE:
            csv_dict["md5"] = self.md5
            csv_dict["sha1"] = self.sha1
            csv_dict["sha256"] = self.sha256
            csv_dict["mime_type"] = self.mime_type

        return csv_dict


class SubmissionTaskProcessData:
    """
    SubmissionTaskProcessData Data Model
    """

    def __init__(
        self, raw_data, progress: int = None, completed: int = None, score: int = None
    ):
        self.raw_data = raw_data
        self.progress = progress
        self.completed = completed
        self.score = score


class SubmissionTaskAnalysisSubject:
    """
    Submission Task Analysis Subject Data Model
    """

    def __init__(
        self,
        raw_data,
        sha256: str = None,
        sha1: str = None,
        mime_type: str = None,
        md5: str = None,
    ):
        self.raw_data = raw_data
        self.sha1 = sha1
        self.sha256 = sha256
        self.mime_type = mime_type
        self.md5 = md5

    def as_csv(self):
        return {
            "md5_hash": self.md5,
            "sha1_hash": self.sha1,
            "sha256_hash": self.sha256,
            "mime_type": self.mime_type,
        }


class Analysis:
    """
    Analysis Model
    """

    def __init__(self, raw_data, success: int = None, data: List = None):
        self.raw_data = raw_data
        self.success = success
        self.data = data

    def as_json(self):
        return self.raw_data

    def as_csv(self):
        return [data_analysis.as_csv() for data_analysis in self.data]


class AnalysisData:
    """
    Analysis Data Model
    """

    def __init__(
        self,
        raw_data,
        username: str = None,
        status: str = None,
        task_subject_filename: str = None,
        task_subject_sha1: str = None,
        task_uuid: str = None,
        task_subject_md5: str = None,
        task_subject_url: str = None,
        task_start_time: str = None,
        analysis_history_id: int = None,
        title: str = None,
        score: int = None,
        **kwargs,
    ):
        self.raw_data = raw_data
        self.username = username
        self.status = status
        self.task_subject_filename = task_subject_filename
        self.task_subject_sha1 = task_subject_sha1
        self.task_uuid = task_uuid
        self.task_subject_md5 = task_subject_md5
        self.task_subject_url = task_subject_url
        self.task_start_time = task_start_time
        self.analysis_history_id = analysis_history_id
        self.title = title
        self.score = score

    def as_json(self):
        return self.raw_data

    def as_csv(self):
        return {
            "Task UUID": self.task_uuid,
            "md5": self.task_subject_md5,
            "sha1": self.task_subject_sha1,
            "Url": self.task_subject_url,
            "Status": self.status,
            "Submitted by (username)": self.username,
            "Submitted at": self.task_start_time,
        }
