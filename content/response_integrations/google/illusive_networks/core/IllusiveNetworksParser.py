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
from .Utils import transform_string_response_to_json
from TIPCommon import SiemplifySession


class IllusiveNetworksParser:

    @staticmethod
    def build_siemplify_host_object(raw_data):
        return HostObject(
            raw_data=raw_data.get("content") if raw_data.get("content") else None,
            machine_name=(
                raw_data.get("content")[0].get("machineName")
                if raw_data.get("content")
                else None
            ),
            is_healthy=(
                raw_data.get("content")[0].get("isHealthy")
                if raw_data.get("content")
                else None
            ),
            host=(
                raw_data.get("content")[0].get("host")
                if raw_data.get("content")
                else None
            ),
            distinguested_name=(
                raw_data.get("content")[0].get("distinguishedName")
                if raw_data.get("content")
                else None
            ),
            source_discovery_name=(
                raw_data.get("content")[0].get("sourceDiscoveryName")
                if raw_data.get("content")
                else None
            ),
            policy_name=(
                raw_data.get("content")[0].get("policyName")
                if raw_data.get("content")
                else None
            ),
            operating_system_name=(
                raw_data.get("content")[0].get("operatingSystemName")
                if raw_data.get("content")
                else None
            ),
            agent_version=(
                raw_data.get("content")[0].get("agentVersion")
                if raw_data.get("content")
                else None
            ),
            logged_in_user_name=(
                raw_data.get("content")[0].get("loggedInUserName")
                if raw_data.get("content")
                else None
            ),
            machine_exe_status=(
                raw_data.get("content")[0].get("machineExecutionUnifiedStatus")
                if raw_data.get("content")
                else None
            ),
            bitness=(
                raw_data.get("content")[0].get("bitness")
                if raw_data.get("content")
                else None
            ),
        )

    @staticmethod
    def build_siemplify_forensic_host_info_object(raw_data):
        value_data = transform_string_response_to_json(raw_data=raw_data)

        return ForensicHostInfo(
            raw_data=value_data,
            os_name=value_data.get("osName"),
            machine_type=value_data.get("machineType"),
            host=value_data.get("host"),
            logged_in_user=value_data.get("loggedInUser"),
            user_profiles=", ".join(value_data.get("userProfiles")),
            operating_system_type=value_data.get("operatingSystemType"),
        )

    @staticmethod
    def build_siemplify_forensic_prefetch_info_object(raw_data):
        prefetch_info_data = transform_string_response_to_json(raw_data=raw_data)

        return [
            ForensicPreFetchInfo(
                raw_data=prefetch_info,
                file_name=prefetch_info.get("fileName") if prefetch_info else None,
                last_exe_time=(
                    prefetch_info.get("details", {}).get("lastExecutionTime")
                    if prefetch_info
                    else None
                ),
                file_modify_time=(
                    prefetch_info.get("details", {}).get("fileModificationTime")
                    if prefetch_info
                    else None
                ),
                prefetchfile_name=(
                    prefetch_info.get("details", {}).get("prefetchFileName")
                    if prefetch_info
                    else None
                ),
            )
            for prefetch_info in prefetch_info_data
        ]

    @staticmethod
    def build_siemplify_forensic_add_remove_object(raw_data):
        add_remove_data = transform_string_response_to_json(raw_data=raw_data)

        return [
            ForensicProgramsInfo(
                raw_data=add_remove,
                display_name=(
                    add_remove.get("details", {}).get("displayName")
                    if add_remove
                    else None
                ),
                file_name=add_remove.get("fileName") if add_remove else None,
            )
            for add_remove in add_remove_data
        ]

    @staticmethod
    def build_siemplify_forensic_startup_object(raw_data):
        startup_processes_data = transform_string_response_to_json(raw_data=raw_data)

        return [
            ForensicStartupProcess(
                raw_data=startup_process,
                name=startup_process.get("Name") if startup_process else None,
                command=startup_process.get("Command") if startup_process else None,
                location=startup_process.get("Location") if startup_process else None,
                user=startup_process.get("User") if startup_process else None,
            )
            for startup_process in startup_processes_data
        ]

    @staticmethod
    def build_siemplify_forensic_runningprocesses_object(raw_data):
        running_processes_data = transform_string_response_to_json(raw_data=raw_data)

        return [
            ForensicRunningProcesses(
                raw_data=running_process,
                user=running_process.get("user") if running_process else None,
                admin_privileges=(
                    running_process.get("administratorPrivilleges")
                    if running_process
                    else None
                ),
                command_line=(
                    running_process.get("commandline") if running_process else None
                ),
                process_id=(
                    running_process.get("processID") if running_process else None
                ),
                process_name=(
                    running_process.get("processName") if running_process else None
                ),
                start_time=(
                    running_process.get("startTime") if running_process else None
                ),
            )
            for running_process in running_processes_data
        ]

    @staticmethod
    def build_siemplify_forensic_userassist_object(raw_data):
        user_assist_data = transform_string_response_to_json(raw_data=raw_data)

        return [
            ForensicUserAssistInfo(
                raw_data=running_process,
                file_name=running_process.get("fileName") if running_process else None,
                user_name=running_process.get("userName") if running_process else None,
                last_updated_date=(
                    running_process.get("lastUsedDate") if running_process else None
                ),
            )
            for running_process in user_assist_data
        ]

    @staticmethod
    def build_siemplify_forensic_powershell_object(raw_data):
        powershell_processes_data = transform_string_response_to_json(raw_data=raw_data)

        return [
            ForensicPowershellInfo(
                raw_data=powershell_process,
                user_name=(
                    powershell_process.get("userName") if powershell_process else None
                ),
                command=(
                    powershell_process.get("command") if powershell_process else None
                ),
            )
            for powershell_process in powershell_processes_data
        ]

    @staticmethod
    def build_siemplify_incident_object(incident_json):
        return Incident(
            raw_data=incident_json,
            incident_time_UTC=incident_json.get("incidentTimeUTC"),
            incident_types=incident_json.get("incidentTypes", []),
            incident_id=incident_json.get("incidentId"),
        )

    @staticmethod
    def build_incident_events(raw_json):
        return [
            BaseModel(raw_data=event_json)
            for event_json in raw_json
            if event_json.get("type") == "EVENT"
        ]

    @staticmethod
    def build_siemplify_deceptive_user_obj_list(raw_json, limit=None):
        return [
            IllusiveNetworksParser.build_siemplify_deceptive_user_obj(deceptive_user)
            for deceptive_user in raw_json[:limit]
        ]

    @staticmethod
    def build_siemplify_deceptive_user_obj(raw_json):
        password = raw_json.get("password", "")
        if password:
            raw_json["password"] = SiemplifySession().encode_data(password)

        return DeceptiveUser(
            raw_data=raw_json,
            username=raw_json.get("username", ""),
            password=raw_json.get("password", ""),
            domain=raw_json.get("domainName", ""),
            policies=raw_json.get("policyNames", []),
            ad_user=raw_json.get("adUser", ""),
            active_user=raw_json.get("activeUser", ""),
            deceptive_state=raw_json.get("deceptiveState", ""),
        )

    @staticmethod
    def build_siemplify_deceptive_server_obj(raw_json):
        return DeceptiveServer(
            raw_data=raw_json,
            host=raw_json.get("host", ""),
            services=raw_json.get("serviceTypes", []),
            policies=raw_json.get("policyNames", []),
            ad_host=raw_json.get("adHost", ""),
            deceptive_state=raw_json.get("deceptiveState", ""),
        )

    @staticmethod
    def build_siemplify_deceptive_server_obj_list(raw_data, limit=None):
        return [
            IllusiveNetworksParser.build_siemplify_deceptive_server_obj(
                deceptive_server
            )
            for deceptive_server in raw_data[:limit]
        ]
