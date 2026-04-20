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
from .datamodels import (
    SubmissionTask,
    SubmissionTaskData,
    SubmissionTaskProcessData,
    SubmissionTaskAnalysisSubject,
    Analysis,
    AnalysisData,
)


class LastlineParser:
    """
    Lastline Parser
    """

    @staticmethod
    def build_submission_task_obj(response, is_get_process: bool) -> SubmissionTask:
        response_json = response.json()
        if is_get_process:
            data = LastlineParser.build_submission_process_data_obj(
                response_json.get("data", {})
            )
        else:
            data = LastlineParser.build_submission_task_data_obj(
                response_json.get("data", {})
            )

        return SubmissionTask(
            raw_data=response_json,
            success=response_json.get("success") or "",
            data=data,
        )

    @staticmethod
    def build_submission_task_data_obj(raw_data) -> SubmissionTaskData:
        analysis_subject = (
            LastlineParser.build_submission_task_analysis_subject_obj(
                raw_data.get("analysis_subject")
            )
            if raw_data.get("analysis_subject")
            else None
        )

        md5 = analysis_subject.md5 if analysis_subject and analysis_subject.md5 else ""
        sha1 = (
            analysis_subject.sha1 if analysis_subject and analysis_subject.sha1 else ""
        )
        sha256 = (
            analysis_subject.sha256
            if analysis_subject and analysis_subject.sha256
            else ""
        )
        mime_type = (
            analysis_subject.mime_type
            if analysis_subject and analysis_subject.mime_type
            else ""
        )

        malicious_activity = raw_data.get("malicious_activity", {})
        # malicious_activity_str = ''
        # if malicious_activity:
        #     for item in malicious_activity:
        #         malicious_activity_str += f"{item}\n"

        return SubmissionTaskData(
            raw_data=raw_data,
            submission=raw_data.get("submission") or "",
            expires=raw_data.get("expires") or "",
            task_uuid=raw_data.get("task_uuid") or "",
            score=raw_data.get("score") if raw_data.get("score") is not None else "",
            analysis_subject=analysis_subject or "",
            malicious_activity=malicious_activity,
            md5=md5,
            sha1=sha1,
            sha256=sha256,
            mime_type=mime_type,
        )

    @staticmethod
    def build_submission_process_data_obj(raw_data) -> SubmissionTaskProcessData:
        return SubmissionTaskProcessData(
            raw_data=raw_data,
            progress=raw_data.get("progress") or "",
            completed=raw_data.get("completed") or "",
            score=raw_data.get("score") if raw_data.get("score") is not None else "",
        )

    @staticmethod
    def build_submission_task_analysis_subject_obj(
        raw_data,
    ) -> SubmissionTaskAnalysisSubject:
        return SubmissionTaskAnalysisSubject(
            raw_data=raw_data,
            sha1=raw_data.get("sha1") or "",
            sha256=raw_data.get("sha256") or "",
            mime_type=raw_data.get("mime_type") or "",
            md5=raw_data.get("md5") or "",
        )

    @staticmethod
    def build_analysis_obj(response) -> Analysis:
        data = [
            LastlineParser.build_analysis_data_obj(analysis_data)
            for analysis_data in response.json().get("data", [])
        ]
        return Analysis(
            raw_data=response.json(), success=response.json().get("success"), data=data
        )

    @staticmethod
    def build_analysis_data_obj(raw_data) -> AnalysisData:
        return AnalysisData(raw_data=raw_data, **raw_data)
