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
from TIPCommon import dict_to_flat, add_prefix_to_dict
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from .constants import ILLUSIVE_NETWORKS_PREFIX


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_flat_dict(self):
        return dict_to_flat(self.to_json())

    def to_csv(self):
        return dict_to_flat(self.to_json())

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class ForensicHostInfo(BaseModel):
    def __init__(
        self,
        raw_data,
        os_name,
        machine_type,
        host,
        logged_in_user,
        user_profiles,
        operating_system_type,
    ):
        super(ForensicHostInfo, self).__init__(raw_data)
        self.os_name = os_name
        self.machine_type = machine_type
        self.host = host
        self.logged_in_user = logged_in_user
        self.user_profiles = user_profiles
        self.operating_system_type = operating_system_type

    def as_enrichment_data(self):
        enrichment_data = {}
        if self.os_name:
            enrichment_data["osName"] = self.os_name
        if self.machine_type:
            enrichment_data["machineType"] = self.machine_type
        if self.host:
            enrichment_data["host"] = self.host
        if self.logged_in_user:
            enrichment_data["loggedInUser"] = self.logged_in_user
        if self.user_profiles:
            enrichment_data["userProfiles"] = self.user_profiles
        if self.operating_system_type:
            enrichment_data["operatingSystemType"] = self.operating_system_type

        return add_prefix_to_dict(
            dict_to_flat(enrichment_data), ILLUSIVE_NETWORKS_PREFIX
        )

    def to_table(self):
        """
        Function that prepares the users's data to be used on the table
        :return {list} List containing dict of users's data
        """

        table_data_list = []

        table_data = {}
        if self.os_name:
            table_data["OS Name"] = self.os_name

        if self.machine_type:
            table_data["Machine Type"] = self.machine_type

        if self.host:
            table_data["Host"] = self.host

        if self.logged_in_user:
            table_data["Logged In User"] = self.logged_in_user

        if self.user_profiles:
            table_data["User Profiles"] = self.user_profiles

        if self.operating_system_type:
            table_data["Operating System Type"] = self.operating_system_type

        for key, value in table_data.items():
            table_data_list.append({"Key": key, "Value": value})

        return table_data_list


class ForensicPreFetchInfo(BaseModel):
    def __init__(
        self, raw_data, file_name, last_exe_time, file_modify_time, prefetchfile_name
    ):
        super(ForensicPreFetchInfo, self).__init__(raw_data)
        self.file_name = file_name
        self.last_exe_time = last_exe_time
        self.file_modify_time = file_modify_time
        self.prefetchfile_name = prefetchfile_name

    def to_table(self):
        table = {
            "File Name": self.file_name,
            "Last Execution Time": self.last_exe_time,
            "File Modification Time": self.file_modify_time,
            "Prefetch File Name": self.prefetchfile_name,
        }
        return table


class ForensicProgramsInfo(BaseModel):
    def __init__(self, raw_data, display_name, file_name):
        super(ForensicProgramsInfo, self).__init__(raw_data)
        self.display_name = display_name
        self.file_name = file_name

    def to_table(self):
        """
        Function that prepares the users's data to be used on the table
        :return {list} List containing dict of users's data
        """

        table = {"File Name": self.file_name, "Display Name": self.display_name}
        return table


class ForensicStartupProcess(BaseModel):
    def __init__(self, raw_data, name, command, location, user):
        super(ForensicStartupProcess, self).__init__(raw_data)
        self.name = name
        self.command = command
        self.location = location
        self.user = user

    def to_table(self):
        table = {
            "User": self.user,
            "Location": self.location,
            "Command": self.command,
            "Name": self.name,
        }
        return table


class ForensicRunningProcesses(BaseModel):
    def __init__(
        self,
        raw_data,
        user,
        admin_privileges,
        command_line,
        process_id,
        process_name,
        start_time,
    ):
        super(ForensicRunningProcesses, self).__init__(raw_data)
        self.user = user
        self.admin_privileges = admin_privileges
        self.command_line = command_line
        self.process_id = process_id
        self.process_name = process_name
        self.start_time = start_time

    def to_table(self):
        table = {
            "User": self.user,
            "Admin Privileges": self.admin_privileges,
            "Command": self.command_line,
            "Process ID": self.process_id,
            "Process Name": self.process_name,
            "Start Time": self.start_time,
        }
        return table


class ForensicUserAssistInfo(BaseModel):
    def __init__(self, raw_data, file_name, user_name, last_updated_date):
        super(ForensicUserAssistInfo, self).__init__(raw_data)
        self.file_name = file_name
        self.user_name = user_name
        self.last_updated_date = last_updated_date

    def to_table(self):
        table = {
            "File Name": self.file_name,
            "User Name": self.user_name,
            "Last Used Date": self.last_updated_date,
        }
        return table


class ForensicPowershellInfo(BaseModel):
    def __init__(self, raw_data, user_name, command):
        super(ForensicPowershellInfo, self).__init__(raw_data)
        self.user_name = user_name
        self.command = command

    def to_table(self):
        table = {"User Name": self.user_name, "Command": self.command}
        return table


class HostObject(BaseModel):

    def __init__(
        self,
        raw_data,
        machine_name,
        is_healthy,
        host,
        distinguested_name,
        source_discovery_name,
        policy_name,
        operating_system_name,
        agent_version,
        logged_in_user_name,
        machine_exe_status,
        bitness,
    ):
        super(HostObject, self).__init__(raw_data)
        self.machine_name = machine_name
        self.is_healthy = is_healthy
        self.host = host
        self.distinguested_name = distinguested_name
        self.source_discovery_name = source_discovery_name
        self.policy_name = policy_name
        self.operating_system_name = operating_system_name
        self.agent_version = agent_version
        self.logged_in_user_name = logged_in_user_name
        self.machine_exe_status = machine_exe_status
        self.bitness = bitness

    def as_enrichment_data(self):
        enrichment_data = {}
        if self.machine_name:
            enrichment_data["machine_name"] = self.machine_name
        if self.is_healthy:
            enrichment_data["is_healthy"] = self.is_healthy
        if self.host:
            enrichment_data["host"] = self.host
        if self.distinguested_name:
            enrichment_data["distinguested_name"] = self.distinguested_name
        if self.source_discovery_name:
            enrichment_data["source_discovery_name"] = self.source_discovery_name
        if self.policy_name:
            enrichment_data["policy_name"] = self.policy_name
        if self.operating_system_name:
            enrichment_data["operating_system_name"] = self.operating_system_name
        if self.agent_version:
            enrichment_data["agent_version"] = self.agent_version
        if self.logged_in_user_name:
            enrichment_data["logged_in_user_name"] = self.logged_in_user_name
        if self.machine_exe_status:
            enrichment_data["machine_exe_status"] = self.machine_exe_status
        if self.bitness:
            enrichment_data["bitness"] = self.bitness

        return add_prefix_to_dict(
            dict_to_flat(enrichment_data), ILLUSIVE_NETWORKS_PREFIX
        )

    def to_table(self):
        """
        Function that prepares the users's data to be used on the table
        :return {list} List containing dict of users's data
        """

        table_data_list = []

        table_data = {}
        if self.machine_name:
            table_data["Machine Name"] = self.machine_name

        if self.is_healthy:
            table_data["Is Healthy"] = self.is_healthy

        if self.host:
            table_data["Host"] = self.host

        if self.distinguested_name:
            table_data["Distinguested Name"] = self.distinguested_name

        if self.source_discovery_name:
            table_data["Source Discovery Name"] = self.source_discovery_name

        if self.policy_name:
            table_data["Policy Name"] = self.policy_name

        if self.operating_system_name:
            table_data["Operating System Name"] = self.operating_system_name

        if self.agent_version:
            table_data["Agent Version"] = self.agent_version

        if self.logged_in_user_name:
            table_data["Loggedin User Name"] = self.logged_in_user_name

        if self.bitness:
            table_data["bitness"] = self.bitness

        for key, value in table_data.items():
            table_data_list.append({"Key": key, "Value": value})

        return table_data_list


class DeceptiveUser(BaseModel):
    def __init__(
        self,
        raw_data,
        username,
        password,
        domain,
        policies,
        ad_user,
        active_user,
        deceptive_state,
    ):
        super(DeceptiveUser, self).__init__(raw_data)
        self.username = username
        self.password = password
        self.domain = domain
        self.policies = policies
        self.ad_user = ad_user
        self.active_user = active_user
        self.deceptive_state = deceptive_state

    def to_table(self):
        return {
            "Username": self.username,
            "Password": self.password,
            "Domain": self.domain,
            "Policies": ", ".join(self.policies),
            "AD User": self.ad_user,
            "Active": self.active_user,
            "State": self.deceptive_state,
        }


class DeceptiveServer(BaseModel):
    def __init__(self, raw_data, host, policies, services, ad_host, deceptive_state):
        super(DeceptiveServer, self).__init__(raw_data)
        self.domain = host
        self.policies = policies
        self.services = services
        self.ad_host = ad_host
        self.deceptive_state = deceptive_state

    def to_table(self):
        return {
            "Host": self.domain,
            "Services": ", ".join(self.services),
            "Policies": ", ".join(self.policies),
            "AD Server": self.ad_host,
            "State": self.deceptive_state,
        }


class Incident(BaseModel):
    def __init__(self, raw_data, incident_time_UTC, incident_id, incident_types):
        super(Incident, self).__init__(raw_data)
        self.incident_time_UTC = incident_time_UTC
        self.timestamp = convert_string_to_unix_time(incident_time_UTC)
        self.incident_id = incident_id
        self.incident_types = incident_types
        self.events = []

    def set_event(self, events):
        self.events = events

    def to_events(self):
        return [dict_to_flat(event.to_json()) for event in self.events]
