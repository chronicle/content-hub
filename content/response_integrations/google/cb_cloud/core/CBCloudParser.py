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
from .datamodels import *


class CBCloudParser:
    # update default data key, or make pure_data property true be default
    def build_results(
        self, raw_json, method, data_key="data", pure_data=False, limit=None, **kwargs
    ):
        return [
            getattr(self, method)(item_json, **kwargs)
            for item_json in (raw_json if pure_data else raw_json.get(data_key, []))[
                :limit
            ]
        ]

    @staticmethod
    def build_siemplify_device_obj(device_data):
        return Device(raw_data=device_data, **device_data)

    @staticmethod
    def build_siemplify_alert_obj(alert_data):
        return Alert(
            raw_data=alert_data,
            alert_type=alert_data.get("type"),
            alert_id=alert_data.get("id"),
            device=CBCloudParser.build_device_object(alert_data),
            watchlists_names=CBCloudParser.get_watchlists_names(alert_data),
            **alert_data,
        )

    @staticmethod
    def build_device_object(alert_data):
        return AlertDevice(
            raw_data=alert_data,
            device_id=alert_data.get("device_id"),
            device_os=alert_data.get("device_os"),
            device_os_version=alert_data.get("device_os_version"),
            device_name=alert_data.get("device_name"),
            device_username=alert_data.get("device_username"),
            device_policy_id=alert_data.get("device_policy_id"),
            device_policy=alert_data.get("device_policy"),
            device_target_value=alert_data.get("device_target_value"),
        )

    @staticmethod
    def get_watchlists_names(alert_data):
        return [watchlist.get("name") for watchlist in alert_data.get("watchlists", [])]

    @staticmethod
    def build_siemplify_enriched_event_obj(event_data):
        return EnrichedEvent(raw_data=event_data, **event_data)

    def get_results(self, raw_json, builder_method=None):
        resources = raw_json.get("results", [])
        return (
            [
                getattr(self, builder_method)(resource_json)
                for resource_json in resources
            ]
            if builder_method
            else resources
        )

    @staticmethod
    def get_job_id(job_result):
        return job_result.get("job_id", "")

    @staticmethod
    def build_siemplify_event_obj(raw_json):
        return Event(
            raw_data=raw_json,
            results=raw_json.get("results", []),
            process_guids=[
                proc.get("process_guid", "") for proc in raw_json.get("results", [])
            ],
        )

    @staticmethod
    def build_event_result_obj(results):
        return Results(raw_data=results, **results)

    @staticmethod
    def build_siemplify_detailed_event_obj(raw_json):
        return DetailedEvent(
            raw_data=raw_json,
            results=CBCloudParser().build_results(
                raw_json=raw_json.get("results", []),
                method="build_event_result_obj",
                pure_data=True,
            ),
            num_found=raw_json.get("num_found", ""),
            num_available=raw_json.get("num_available", ""),
            approximate_unaggregated=raw_json.get("approximate_unaggregated", ""),
            num_aggregated=raw_json.get("num_aggregated", ""),
            contacted=raw_json.get("contacted", ""),
            completed=raw_json.get("completed", ""),
        )

    @staticmethod
    def get_contacted_status(raw_json):
        return raw_json.get("contacted", 0)

    @staticmethod
    def get_found_number(raw_json):
        return raw_json.get("num_found", 0)

    @staticmethod
    def get_completed_status(raw_json):
        return raw_json.get("completed", 1)

    @staticmethod
    def get_job_statuses(raw_json):
        return raw_json.get("completed", 1), raw_json.get("contacted", 0)

    @staticmethod
    def build_reputation_override_obj_list(raw_json):
        objs = []
        for raw_rep in raw_json.get("results", []):
            override_type = raw_rep.get("override_type")
            if override_type == "CERT":
                objs.append(
                    CBCloudParser.build_certificate_reputation_override_obj(raw_rep)
                )
            elif override_type == "SHA256":
                objs.append(CBCloudParser.build_sha265_reputation_override_obj(raw_rep))
            elif override_type == "IT_TOOL":
                objs.append(
                    CBCloudParser.build_it_tool_reputation_override_obj(raw_rep)
                )
            else:
                # Unrecognized reputation override type
                objs.append(
                    OverriddenReputation(
                        raw_data=raw_json,
                        id=raw_json.get("id"),
                        created_by=raw_json.get("created_by"),
                        create_time=raw_json.get("create_time"),
                        override_list=raw_json.get("override_list"),
                        override_type=raw_json.get("override_type"),
                        description=raw_json.get("description"),
                        source=raw_json.get("source"),
                        source_ref=raw_json.get("source_ref"),
                    )
                )
        return objs

    @staticmethod
    def build_it_tool_reputation_override_obj(raw_json):
        return OverriddenITToolReputation(
            raw_data=raw_json,
            id=raw_json.get("id"),
            created_by=raw_json.get("created_by"),
            create_time=raw_json.get("create_time"),
            override_list=raw_json.get("override_list"),
            override_type=raw_json.get("override_type"),
            description=raw_json.get("description"),
            source=raw_json.get("source"),
            source_ref=raw_json.get("source_ref"),
            path=raw_json.get("path"),
            include_child_processes=raw_json.get("include_child_processes"),
        )

    @staticmethod
    def build_certificate_reputation_override_obj(raw_json):
        return OverriddenCertificateReputation(
            raw_data=raw_json,
            id=raw_json.get("id"),
            created_by=raw_json.get("created_by"),
            create_time=raw_json.get("create_time"),
            override_list=raw_json.get("override_list"),
            override_type=raw_json.get("override_type"),
            description=raw_json.get("description"),
            source=raw_json.get("source"),
            source_ref=raw_json.get("source_ref"),
            signed_by=raw_json.get("signed_by"),
            certificate_authority=raw_json.get("certificate_authority"),
        )

    @staticmethod
    def build_sha265_reputation_override_obj(raw_json):
        return OverriddenSHA256Reputation(
            raw_data=raw_json,
            id=raw_json.get("id"),
            created_by=raw_json.get("created_by"),
            create_time=raw_json.get("create_time"),
            override_list=raw_json.get("override_list"),
            override_type=raw_json.get("override_type"),
            description=raw_json.get("description"),
            source=raw_json.get("source"),
            source_ref=raw_json.get("source_ref"),
            sha256_hash=raw_json.get("sha256_hash"),
            filename=raw_json.get("filename"),
        )

    @staticmethod
    def build_vulnerability_detail(raw_data):
        return VulnerabilityDetail(
            raw_data=raw_data,
            cve_id=raw_data.get("vuln_info", {}).get("cve_id"),
            score=raw_data.get("vuln_info", {}).get("risk_meter_score"),
            severity=raw_data.get("vuln_info", {}).get("severity"),
            cve_description=raw_data.get("vuln_info", {}).get("cve_description"),
        )
