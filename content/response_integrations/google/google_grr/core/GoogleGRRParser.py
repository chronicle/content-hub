from __future__ import annotations
from .consts import WEEK_IN_SECONDS
from .utils import get_date_from_rdf_dateframe, add_duration_to_date
from TIPCommon import dict_to_flat
from .datamodels import Client, AgentInfo, VolumeInfo, HardwareInfo, OSInfo
from .datamodels import Flow, Hunt


class GoogleGRRParser:
    """
    GoogleGRR parser
    """

    @staticmethod
    def build_clients_obj(objects_data):
        return [
            GoogleGRRParser.build_client_obj(client)
            for client in objects_data.get("items", [])
        ]

    @staticmethod
    def build_client_obj_from_client_id(objects_data):
        objects_data = objects_data.get("items", [])
        return (
            GoogleGRRParser.build_client_obj(objects_data[0]) if objects_data else None
        )

    @staticmethod
    def build_client_obj(objects_data):
        data = objects_data.get("value", {})

        agent_info = GoogleGRRParser.build_agent_info_obj(
            data.get("agent_info", {}).get("value", {})
        )
        os_info = GoogleGRRParser.build_os_info_obj(
            data.get("os_info", {}).get("value", {})
        )
        hardware_info_value = GoogleGRRParser.build_hardware_info_obj(
            data.get("hardware_info", {}).get("value", {})
        )
        volumes_info = []

        for volume in data.get("volumes", {}):
            volumes_info.append(
                GoogleGRRParser.build_volume_info_obj(volume.get("value", {}))
            )

        client_last_booted_at = get_date_from_rdf_dateframe("last_booted_at", data)
        client_first_seen_at = get_date_from_rdf_dateframe("first_seen_at", data)
        client_last_seen_at = get_date_from_rdf_dateframe("last_seen_at", data)
        client_last_clock = get_date_from_rdf_dateframe("last_clock", data)
        last_crash_at = get_date_from_rdf_dateframe("last_crash_at", data)

        users_value = data.get("knowledge_base", {}).get("value", {}).get("users", [])

        return Client(
            raw_data=data,
            agent_info_obj=agent_info,
            client_last_booted_at=client_last_booted_at,
            client_first_seen_at=client_first_seen_at,
            client_last_seen_at=client_last_seen_at,
            client_last_clock=client_last_clock,
            last_crash_at=last_crash_at,
            os_info_obj=os_info,
            hardware_info_value=hardware_info_value,
            volumes_info=volumes_info,
            users_value=users_value,
            **data,
        )

    @staticmethod
    def build_agent_info_obj(objects_data):
        return AgentInfo(raw_data=objects_data, **objects_data)

    @staticmethod
    def build_os_info_obj(objects_data):
        installation_time = get_date_from_rdf_dateframe("install_date", objects_data)
        return OSInfo(
            raw_data=objects_data, installation_time=installation_time, **objects_data
        )

    @staticmethod
    def build_hardware_info_obj(objects_data):
        system_product_name = objects_data.get("system_product_name", {}).get(
            "value", ""
        )
        bios_rom_size = objects_data.get("bios_rom_size", {}).get("value", "")
        bios_vendor = objects_data.get("bios_vendor", {}).get("value", "")
        system_sku_number = objects_data.get("system_sku_number", {}).get("value", "")
        system_family = objects_data.get("system_family", {}).get("value", "")
        system_manufacturer = objects_data.get("system_manufacturer", {}).get(
            "value", ""
        )
        bios_release_date = objects_data.get("bios_release_date", {}).get("value", "")
        bios_version = objects_data.get("bios_version", {}).get("value", "")
        serial_number = objects_data.get("serial_number", {}).get("value", "")
        bios_revision = objects_data.get("bios_revision", {}).get("value", "")

        return HardwareInfo(
            raw_data=objects_data,
            system_product_name_value=system_product_name,
            bios_rom_size_value=bios_rom_size,
            bios_vendor_value=bios_vendor,
            system_sku_number_value=system_sku_number,
            system_family_value=system_family,
            system_manufacturer_value=system_manufacturer,
            bios_release_date_value=bios_release_date,
            bios_version_value=bios_version,
            serial_number_value=serial_number,
            bios_revision_value=bios_revision,
            **objects_data,
        )

    @staticmethod
    def build_volume_info_obj(objects_data):
        total_allocation_units = objects_data.get("total_allocation_units", {}).get(
            "value", ""
        )
        bytes_per_sector = objects_data.get("bytes_per_sector", {}).get("value", "")
        sectors_per_allocation_unit = objects_data.get(
            "sectors_per_allocation_unit", {}
        ).get("value", "")
        unixvolume = {
            "mount_point": objects_data.get("unixvolume", {})
            .get("value", {})
            .get("mount_point", {})
            .get("value", "")
        }

        return VolumeInfo(
            raw_data=objects_data,
            total_allocation_units_value=total_allocation_units,
            bytes_per_sector_value=bytes_per_sector,
            sectors_per_allocation_unit_value=sectors_per_allocation_unit,
            unixvolume_value=unixvolume,
        )

    @staticmethod
    def build_flows_obj(objects_data):
        return [
            GoogleGRRParser.build_flow_obj(flow)
            for flow in objects_data.get("items", [])
        ]

    @staticmethod
    def build_flow_obj(objects_data):
        creator_value = (
            objects_data.get("value", {}).get("creator", {}).get("value", {})
        )
        state_value = objects_data.get("value", {}).get("state", {}).get("value", "")
        started_at_value = get_date_from_rdf_dateframe(
            "started_at", objects_data.get("value", {})
        )
        last_active_at_value = get_date_from_rdf_dateframe(
            "last_active_at", objects_data.get("value", {})
        )
        flow_id_value = (
            objects_data.get("value", {}).get("flow_id", {}).get("value", "")
        )
        flow_name_value = objects_data.get("value", {}).get("name", {}).get("value", "")

        args_runner = dict(
            objects_data.get("value", {})
            .get("runner_args", {})
            .get("value", {})
            .items()
        )
        args_value = {}

        for key in args_runner.keys():
            if key == "output_plugins":
                args_value[key] = args_runner[key]
            else:
                args_value[key] = args_runner[key].get("value", {})

        nested_flows_value = [
            GoogleGRRParser.build_flow_obj(flow)
            for flow in objects_data.get("value", {}).get("nested_flows", {})
        ]

        return Flow(
            raw_data=objects_data,
            creator_value=creator_value,
            state_value=state_value,
            started_at_value=started_at_value,
            last_active_at_value=last_active_at_value,
            flow_id_value=flow_id_value,
            flow_name_value=flow_name_value,
            nested_flows_value=nested_flows_value,
            args_value=args_value,
            **objects_data,
        )

    @staticmethod
    def build_hunts_obj(objects_data):
        data = objects_data.get("items", [])
        return [GoogleGRRParser.build_hunt_obj(hunt_details) for hunt_details in data]

    @staticmethod
    def build_hunt_obj(objects_data):
        flattened_data = dict_to_flat(objects_data.get("value", {}))

        creation_time_value = get_date_from_rdf_dateframe(
            "created", objects_data.get("value")
        )
        last_start_time_value = get_date_from_rdf_dateframe(
            "last_start_time", objects_data.get("value")
        )
        init_start_time_value = get_date_from_rdf_dateframe(
            "init_start_time", objects_data.get("value")
        )
        expiration_time_value = ""

        if flattened_data.get("duration_value") and flattened_data.get(
            "init_start_time_value"
        ):
            expiration_time_value = add_duration_to_date(
                rdf_time=flattened_data.get("init_start_time_value"),
                duration=flattened_data.get("duration_value"),
            )

        duration_value = int(flattened_data.get("duration_value")) / WEEK_IN_SECONDS
        duration_value = int(duration_value)

        total_cpu_time_used_value = flattened_data.get("total_cpu_usage_value", "")
        total_cpu_time_used_value = (
            round(float(total_cpu_time_used_value)) if total_cpu_time_used_value else 0
        )
        total_network_traffic_value = flattened_data.get("total_net_usage_value", "")
        total_network_traffic_value = (
            int(float(total_network_traffic_value))
            if total_network_traffic_value
            else 0
        )

        flow_args = {}

        if objects_data.get("value", {}).get("flow_args", {}):
            for key, value in (
                objects_data.get("value", {})
                .get("flow_args", {})
                .get("value", {})
                .items()
            ):
                flow_args[key] = value.get("value", "")

        return Hunt(
            raw_data=objects_data,
            hunt_description_value=flattened_data.get("description_value", ""),
            creator_value=flattened_data.get("creator_value", ""),
            is_robot_value=flattened_data.get("is_robot_value", ""),
            state_value=flattened_data.get("state_value", ""),
            duration_value=str(duration_value) + "w",
            client_limit_value=flattened_data.get("client_limit_value", ""),
            hunt_id_value=flattened_data.get("hunt_id_value", ""),
            creation_time_value=creation_time_value,
            last_start_time_value=last_start_time_value,
            init_start_time_value=init_start_time_value,
            expiration_time_value=expiration_time_value,
            name_value=flattened_data.get("name_value", ""),
            crash_limit_value=flattened_data.get("crash_limit_value", ""),
            client_rate_value=flattened_data.get("client_rate_value", ""),
            clients_queued_count_value=flattened_data.get(
                "clients_queued_count_value", ""
            ),
            client_scheduled_value=flattened_data.get("all_clients_count_value", ""),
            client_outstanding_value=flattened_data.get(
                "remaining_clients_count_value", ""
            ),
            client_completed_value=flattened_data.get(
                "completed_clients_count_value", ""
            ),
            client_with_results_value=flattened_data.get(
                "clients_with_results_count_value", ""
            ),
            result_value=flattened_data.get("results_count_value", ""),
            total_cpu_time_used_value=f"{str(total_cpu_time_used_value)}s",
            total_network_traffic_value=total_network_traffic_value,
            flow_name_value=flattened_data.get("flow_name_value", ""),
            flow_args_value=flow_args,
            client_rule_set_value=flattened_data.get("client_rule_set_value", ""),
            **objects_data,
        )
