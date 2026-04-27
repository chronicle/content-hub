from __future__ import annotations
from . import utils


class Client:
    """
    GoogleGRR Client
    """

    def __init__(
        self,
        raw_data,
        client_id=None,
        agent_info_obj=None,
        os_info_obj=None,
        client_last_booted_at=None,
        client_first_seen_at=None,
        client_last_seen_at=None,
        client_last_clock=None,
        memory_size=None,
        client_labels=None,
        interfaces=None,
        hardware_info_value=None,
        volumes_info=None,
        last_crash_at=None,
        users_value=None,
        **kwargs
    ):
        """
        Client Constructor
        """
        self.raw_data = raw_data
        self.client_id = client_id.get("value", "")
        self.agent_info = agent_info_obj
        self.os_info = os_info_obj
        self.hardware_info_value = hardware_info_value
        self.volumes_info = volumes_info
        self.client_last_booted_at = client_last_booted_at
        self.client_first_seen_at = client_first_seen_at
        self.client_last_seen = client_last_seen_at
        self.client_last_clock = client_last_clock
        self.last_crash_at = last_crash_at
        self.memory_size = utils.convert_size(memory_size.get("value", 0))
        self.client_labels = client_labels if client_labels else []
        self.interfaces = interfaces
        self.users = users_value

    def as_json(self):
        return {
            "Client_ID": self.client_id,
            "Agent_Info": {
                "Client_Name": self.agent_info.client_name,
                "Client_Version": self.agent_info.client_version,
            },
            "OS_Info": {
                "System": self.os_info.system,
                "Release": self.os_info.release,
                "Architecture": self.os_info.architecture,
                "Installation_Time": self.os_info.installation_time,
                "Kernel": self.os_info.kernel,
                "Version": self.os_info.version,
            },
            "Client_Last_Booted_At": self.client_last_booted_at,
            "Client_First_Seen_At": self.client_first_seen_at,
            "Client_Last_Seen": self.client_last_seen,
            "Client_Last_Clock": self.client_last_clock,
            "Memory_Size": self.memory_size if self.memory_size else "",
            "Client_Labels": self.client_labels if self.client_labels else [],
        }

    def as_json_by_id(self):
        return {
            "HardwareInfo": self.hardware_info_value.as_json(),
            "LastClock": self.client_last_clock,
            "Interfaces": utils.extract_interfaces(self.interfaces),
            "OS": {
                "kernel": self.os_info.kernel,
                "install_date": self.os_info.installation_time,
                "system": self.os_info.system,
                "fqdn": self.raw_data.get("fqdn"),
                "machine": self.os_info.architecture,
                "version": self.os_info.version,
                "release": self.os_info.release,
            },
            "AgentInfo": {
                "client_name": self.agent_info.client_name,
                "client_description": self.agent_info.client_description,
                "client_version": self.agent_info.client_version,
                "build_time": self.agent_info.build_time,
            },
            "Labels": self.client_labels if self.client_labels else [],
            "LastBootedAt": self.client_last_booted_at,
            "FirstSeenAt": self.client_first_seen_at,
            "User": self.users,
            "Volumes": [volume.as_json() for volume in self.volumes_info],
            "LastCrashAt": self.last_crash_at,
            "ID": self.client_id,
        }

    def as_csv(self):
        return {
            "Client ID": self.client_id,
            "Host": self.os_info.fqdn,
            "OS Version": self.os_info.version,
            "First Seen": self.client_first_seen_at,
            "Client Version": self.agent_info.client_version,
            "Labels": self.client_labels,
            "Last Check In": self.client_last_seen,
            "OS Install Date": self.os_info.installation_time,
        }

    def as_csv_by_id(self):
        return {
            "Client ID": self.client_id,
            "Host": self.os_info.fqdn,
            "OS Version": self.os_info.version,
            "Labels": self.client_labels,
            "Memory_Size": self.memory_size if self.memory_size else "",
            "Client Version": self.agent_info.client_version,
            "First Seen": self.client_first_seen_at,
            "Last Seen": self.client_last_seen,
            "OS Install Date": self.os_info.installation_time,
        }


class Flow:
    def __init__(
        self,
        raw_data,
        creator_value=None,
        state_value=None,
        started_at_value=None,
        last_active_at_value=None,
        flow_id_value=None,
        flow_name_value=None,
        nested_flows_value=None,
        args_value=None,
        **kwargs
    ):

        self.raw_data = raw_data
        self.creator = creator_value
        self.started_at = started_at_value
        self.state = state_value
        self.last_active_at = last_active_at_value
        self.flow_id = flow_id_value
        self.flow_name = flow_name_value
        self.nested_flows = nested_flows_value
        self.args = args_value

    def as_json(self):
        return {
            "Creator": self.creator,
            "NestedFlow": [flow.as_json() for flow in self.nested_flows],
            "LastActiveAt": self.last_active_at,
            "Args": self.args,
            "State": self.state,
            "StartedAt": self.started_at,
            "Flow_ID": self.flow_id,
            "Flow_Name": self.flow_name,
        }

    def as_csv(self):
        return {
            "Flow Name": self.flow_name,
            "Flow ID": self.flow_id,
            "State": self.state,
            "Creation Time": self.started_at,
            "Last Active": self.last_active_at,
            "Creator": self.creator,
        }


class Hunt:
    def __init__(
        self,
        raw_data,
        hunt_description_value=None,
        creator_value=None,
        is_robot_value=None,
        state_value=None,
        creation_time_value=None,
        init_start_time_value=None,
        last_start_time_value=None,
        duration_value=None,
        client_limit_value=None,
        hunt_id_value=None,
        expiration_time_value=None,
        name_value=None,
        crash_limit_value=None,
        client_rate_value=None,
        clients_queued_count_value=None,
        client_scheduled_value=None,
        client_outstanding_value=None,
        client_completed_value=None,
        client_with_results_value=None,
        result_value=None,
        total_cpu_time_used_value=None,
        total_network_traffic_value=None,
        flow_name_value=None,
        flow_args_value=None,
        client_rule_set_value=None,
        **kwargs
    ):

        self.raw_data = raw_data
        self.hunt_description = hunt_description_value
        self.creator = creator_value
        self.hunt_id = hunt_id_value
        self.is_robot = is_robot_value
        self.state = state_value
        self.creation_time = creation_time_value
        self.init_start_time = init_start_time_value
        self.last_start_time = last_start_time_value
        self.duration = duration_value
        self.client_limit = client_limit_value
        self.expiration_time = expiration_time_value
        self.name = name_value
        self.crash_limit = crash_limit_value
        self.client_rate = client_rate_value
        self.clients_queued_count = clients_queued_count_value
        self.client_scheduled = client_scheduled_value
        self.client_outstanding = client_outstanding_value
        self.client_completed = client_completed_value
        self.client_with_results = client_with_results_value
        self.result = result_value
        self.total_cpu_time_used = total_cpu_time_used_value
        self.total_network_traffic = utils.convert_size(total_network_traffic_value)
        self.flow_name = flow_name_value
        self.flow_args = flow_args_value
        self.client_rule_set = client_rule_set_value

    def as_json(self):
        return {
            "Hunt_Description": self.hunt_description,
            "Creator": self.creator,
            "Is_Robot": self.is_robot,
            "State": self.state,
            "Creation Time": self.creation_time,
            "Start Time (initial)": self.init_start_time,
            "Start Time (last)": self.last_start_time,
            "Duration": self.duration,
            "Client Limit": self.client_limit,
            "Expiration Time": self.expiration_time,
            "Hunt_ID": self.hunt_id,
        }

    def as_json_by_id(self):
        return {
            "Name": self.name,
            "Description": self.hunt_description,
            "Creator": self.creator,
            "IsRobot": self.is_robot,
            "Status": self.state,
            "Hunt_ID": self.hunt_id,
            "Created": self.creation_time,
            "Start_Time": self.init_start_time,
            "Duration": self.duration,
            "Expiration time": self.expiration_time,
            "Crash_limit": self.crash_limit,
            "Client_limit": self.client_limit,
            "Client_rate (clients/min)": self.client_rate,
            "Client_Queued": self.clients_queued_count,
            "Client_Scheduled": self.client_scheduled,
            "Client_Outstanding": self.client_outstanding,
            "Client_Completed": self.client_with_results,
            "Client_with Results": self.client_with_results,
            "Results": self.result,
            "Total_CPU_Time_Used": self.total_cpu_time_used,
            "Total_Network_Traffic": self.total_network_traffic,
            "Flow_Name": self.flow_name,
            "Flow_Arguments": self.flow_args,
            "Client_Rule_Set": self.client_rule_set,
        }

    def as_csv(self):
        return {
            "Hunt ID": self.hunt_id,
            "Status": self.state,
            "Creation Time": self.creation_time,
            "Start Time": self.last_start_time,
            "Duration": self.duration,
            "Client Limit": self.client_limit,
            "Expiration Time": self.expiration_time,
            "Creator": self.creator,
            "Hunt Description": self.hunt_description,
        }


class AgentInfo:
    def __init__(
        self,
        raw_data,
        client_name,
        client_version,
        client_description,
        build_time,
        **kwargs
    ):
        """
        AgentInfo Constructor
        """
        self.raw_data = raw_data
        self.client_name = client_name.get("value", "")
        self.client_version = client_version.get("value", "")
        self.client_description = client_description.get("value", "")
        self.build_time = build_time.get("value", "")


class OSInfo:
    def __init__(
        self,
        raw_data,
        system,
        release,
        machine,
        installation_time,
        kernel,
        version,
        fqdn,
        **kwargs
    ):
        """
        OSInfo Constructor
        """
        self.raw_data = raw_data
        self.system = system.get("value", "")
        self.release = release.get("value", "")
        self.architecture = machine.get("value", "")
        self.installation_time = installation_time
        self.kernel = kernel.get("value", "")
        self.version = version.get("value", "")
        self.fqdn = fqdn.get("value", "")


class HardwareInfo:
    """
    HardwareInfo Constructor
    """

    def __init__(
        self,
        raw_data,
        system_product_name_value,
        bios_rom_size_value,
        bios_vendor_value,
        system_sku_number_value,
        system_family_value,
        system_manufacturer_value,
        bios_release_date_value,
        bios_version_value,
        serial_number_value,
        bios_revision_value,
        **kwargs
    ):
        self.raw_data = raw_data
        self.system_product_name_value = system_product_name_value
        self.bios_rom_size_value = bios_rom_size_value
        self.bios_vendor_value = bios_vendor_value
        self.system_sku_number_value = system_sku_number_value
        self.system_family_value = system_family_value
        self.system_manufacturer_value = system_manufacturer_value
        self.bios_release_date_value = bios_release_date_value
        self.bios_version_value = bios_version_value
        self.serial_number_value = serial_number_value
        self.bios_revision_value = bios_revision_value

    def as_json(self):
        return {
            "system_product_name": self.system_product_name_value,
            "bios_rom_size": self.bios_rom_size_value,
            "bios_vendor": self.bios_vendor_value,
            "system_sku_number": self.system_sku_number_value,
            "system_family": self.system_family_value,
            "system_manufacturer": self.system_manufacturer_value,
            "bios_release_date": self.bios_release_date_value,
            "bios_version": self.bios_version_value,
            "serial_number": self.serial_number_value,
            "bios_revision": self.bios_revision_value,
        }


class VolumeInfo:
    """
    VolumeInfo Constructor
    """

    def __init__(
        self,
        raw_data,
        total_allocation_units_value,
        bytes_per_sector_value,
        sectors_per_allocation_unit_value,
        unixvolume_value,
    ):
        self.raw_data = raw_data
        self.total_allocation_units_value = total_allocation_units_value
        self.bytes_per_sector_value = bytes_per_sector_value
        self.sectors_per_allocation_unit_value = sectors_per_allocation_unit_value
        self.unixvolume_value = unixvolume_value

    def as_json(self):
        return {
            "total_allocation_units": self.total_allocation_units_value,
            "bytes_per_sector": self.bytes_per_sector_value,
            "sectors_per_allocation_unit": self.sectors_per_allocation_unit_value,
            "unixvolume": self.unixvolume_value,
        }
