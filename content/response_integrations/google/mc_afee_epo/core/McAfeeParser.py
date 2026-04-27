from __future__ import annotations
import re
from .datamodels import *


class McAfeeParser:
    def build_results(self, raw_json, method, data_key=None, limit=None, *kwargs):
        return [
            getattr(self, method)(item_json, *kwargs)
            for item_json in (raw_json.get(data_key, []) if data_key else raw_json)[
                :limit
            ]
        ]

    def build_result(self, raw_json, method, *kwargs):
        return getattr(self, method)(raw_json.get("data", {}), *kwargs)

    @staticmethod
    def build_group(raw_json):
        return Group(
            raw_data=raw_json,
            group_id=raw_json.get("groupId"),
            group_path=raw_json.get("groupPath"),
        )

    def build_system_information(self, system_information_data):
        return SystemInformation(
            raw_data=system_information_data,
            **self._change_param_names(system_information_data)
        )

    def build_vsav(self, raw_json):
        return VirusScanVersion(raw_data=raw_json, **self._change_param_names(raw_json))

    def build_machine_guid(self, machine_guid_data):
        return MachineGUID(
            raw_data=machine_guid_data, **self._change_param_names(machine_guid_data)
        )

    def build_last_communication_time(self, raw_json):
        return LastCommunicationTime(
            raw_data=raw_json, **self._change_param_names(raw_json)
        )

    def build_custom_query(self, raw_json):
        return CustomQuery(raw_data=raw_json, **self._change_param_names(raw_json))

    def build_epo_event(self, raw_json):
        return EPOEvent(raw_data=raw_json, **self._change_param_names(raw_json))

    def build_epo_extended_event(self, raw_json):
        return EPExtendedEvent(raw_data=raw_json, **self._change_param_names(raw_json))

    def build_epo_entity_event(self, raw_json):
        return EPEEntityEvent(raw_data=raw_json, **self._change_param_names(raw_json))

    def _change_param_names(self, data):
        return {
            self._covert_camel_to_snake(key.split(".")[-1]): value
            for key, value in data.items()
        }

    def build_endpoint_event(self, raw_json):
        return EPEndpointEvent(raw_data=raw_json, **self._change_param_names(raw_json))

    def build_threat(self, raw_json):
        return Threat(raw_data=raw_json, **self._change_param_names(raw_json))

    def build_task(self, raw_json):
        return Task(
            raw_data=raw_json,
            product_id=raw_json.get("productId"),
            type_name=raw_json.get("typeName"),
            type_id=raw_json.get("typeId"),
            object_name=raw_json.get("objectName", ""),
            prevention=raw_json.get("Prevention"),
            object_id=raw_json.get("objectId"),
            product_name=raw_json.get("productName", ""),
        )

    def build_query(self, raw_json):
        return Query(
            raw_data=raw_json,
            query_id=raw_json.get("id"),
            name=raw_json.get("name", ""),
            description=raw_json.get("description", ""),
        )

    def build_task_status(self, raw_json):
        return TaskStatus(raw_data=raw_json)

    def build_query_result(self, raw_json):
        return QueryResult(raw_data=raw_json)

    @staticmethod
    def _covert_camel_to_snake(camel):
        camel = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", camel)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", camel).lower().replace("__", "_")

    def build_hip_property(self, raw_data):
        return HipProperty(raw_data=raw_data, **self._change_param_names(raw_data))

    def build_dat_version(self, raw_data):
        return DatVersion(raw_data=raw_data, **self._change_param_names(raw_data))

    def build_server_dat(self, raw_data):
        return ServerDat(raw_data=raw_data, **self._change_param_names(raw_data))
