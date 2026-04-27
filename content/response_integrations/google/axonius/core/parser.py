from __future__ import annotations
from typing import List, Dict, Optional

from .datamodels import (
    UserGeneralAttribute,
    DeviceGeneralAttribute,
    UserDetailedInformation,
    DeviceDetailedInformation,
    UserNote,
    DeviceNote,
)


class AxoniusTransformationLayer:

    @staticmethod
    def parse_api_http_error_response(raw_response: Dict) -> str:
        errors = raw_response.get("errors", [])
        return "   ".join(error.get("detail", "") for error in errors) or raw_response

    @staticmethod
    def build_user_general_attribute_obj_list(
        raw_response: Dict,
    ) -> List[UserGeneralAttribute]:
        return [
            UserGeneralAttribute(
                raw_data=raw_attribute,
                internal_axon_id=raw_attribute.get("attributes", {}).get(
                    "internal_axon_id"
                ),
                usernames=raw_attribute.get("attributes", {}).get(
                    "specific_data.data.username", [None]
                ),
                display_names=raw_attribute.get("attributes", {}).get(
                    "specific_data.data.display_name", [None]
                ),
                emails=raw_attribute.get("attributes", {}).get(
                    "specific_data.data.mail", [None]
                ),
            )
            for raw_attribute in raw_response.get("data", [])
        ]

    @staticmethod
    def build_user_detailed_information_obj(
        raw_response: Dict, api_root: Optional[str] = None
    ) -> UserDetailedInformation:
        raw_response = raw_response.get("data", {})
        adapters = AxoniusTransformationLayer.build_user_detailed_information_adapters_obj_list(
            raw_response.get("attributes", {}).get("adapters", [])
        )
        # Find entity data adapter
        entity_data_adapter = next(
            filter(lambda adapter: adapter.is_entity_data_adapter, adapters), None
        )
        return UserDetailedInformation(
            raw_data=raw_response,
            internal_axon_id=raw_response.get("attributes", {}).get("internal_axon_id"),
            labels=raw_response.get("attributes", {}).get("labels", []),
            adapters=adapters,
            account_disabled=(
                entity_data_adapter.raw_data.get("data", {}).get("account_disabled")
                if entity_data_adapter
                else None
            ),
            ad_display_name=(
                entity_data_adapter.raw_data.get("data", {}).get("ad_display_name")
                if entity_data_adapter
                else None
            ),
            ad_distinguished_name=(
                entity_data_adapter.raw_data.get("data", {}).get(
                    "ad_distinguished_name"
                )
                if entity_data_adapter
                else None
            ),
            ad_sid=(
                entity_data_adapter.raw_data.get("data", {}).get("ad_sid")
                if entity_data_adapter
                else None
            ),
            employee_id=(
                entity_data_adapter.raw_data.get("data", {}).get("employee_id")
                if entity_data_adapter
                else None
            ),
            is_admin=(
                entity_data_adapter.raw_data.get("data", {}).get("is_admin")
                if entity_data_adapter
                else None
            ),
            is_local=(
                entity_data_adapter.raw_data.get("data", {}).get("is_local")
                if entity_data_adapter
                else None
            ),
            is_locked=(
                entity_data_adapter.raw_data.get("data", {}).get("is_locked")
                if entity_data_adapter
                else None
            ),
            mail=(
                entity_data_adapter.raw_data.get("data", {}).get("mail")
                if entity_data_adapter
                else None
            ),
            user_telephone_number=(
                entity_data_adapter.raw_data.get("data", {}).get(
                    "user_telephone_number"
                )
                if entity_data_adapter
                else None
            ),
            display_name=(
                entity_data_adapter.raw_data.get("data", {}).get("display_name")
                if entity_data_adapter
                else None
            ),
            username=(
                entity_data_adapter.raw_data.get("data", {}).get("username")
                if entity_data_adapter
                else None
            ),
            api_root=api_root,
            notes=AxoniusTransformationLayer.build_user_detailed_information_notes_obj_list(
                raw_response
            ),
        )

    @staticmethod
    def build_user_detailed_information_adapters_obj_list(
        raw_adapters: List[Dict],
    ) -> List[UserDetailedInformation.Adapter]:
        return [
            AxoniusTransformationLayer.build_user_detailed_information_adapter_obj(
                raw_adapter
            )
            for raw_adapter in raw_adapters
        ]

    @staticmethod
    def build_user_detailed_information_adapter_obj(
        raw_adapter: Dict,
    ) -> UserDetailedInformation.Adapter:
        return UserDetailedInformation.Adapter(
            raw_data=raw_adapter,
            adapter_type=raw_adapter.get("type"),
            data_raw=raw_adapter.get("data", {}).get("raw"),
        )

    @staticmethod
    def build_user_detailed_information_notes_obj_list(
        raw_response: Dict,
    ) -> List[UserDetailedInformation.Note]:
        attributes_data = raw_response.get("attributes", {}).get("data", [])
        if attributes_data:
            return [
                AxoniusTransformationLayer.build_user_detailed_information_note_obj(
                    raw_note
                )
                for raw_note in attributes_data[0].get("data", [])
            ]

    @staticmethod
    def build_user_detailed_information_note_obj(
        raw_note: Dict,
    ) -> UserDetailedInformation.Note:
        return UserDetailedInformation.Note(
            raw_data=raw_note,
            accurate_for_datetime=raw_note.get("accurate_for_datetime"),
            note=raw_note.get("note"),
            user_name=raw_note.get("user_name"),
            user_id=raw_note.get("user_id"),
        )

    @staticmethod
    def build_device_general_attribute_obj_list(
        raw_response: Dict,
    ) -> List[DeviceGeneralAttribute]:
        return [
            DeviceGeneralAttribute(
                raw_data=raw_attribute,
                internal_axon_id=raw_attribute.get("attributes", {}).get(
                    "internal_axon_id"
                ),
                ips=raw_attribute.get("attributes", {}).get(
                    "specific_data.data.network_interfaces.ips"
                ),
                macs=raw_attribute.get("attributes", {}).get(
                    "specific_data.data.network_interfaces.mac"
                ),
                name=raw_attribute.get("attributes", {}).get(
                    "specific_data.data.name", [None]
                )[0],
                hostname=raw_attribute.get("attributes", {}).get(
                    "specific_data.data.hostname", [None]
                )[0],
            )
            for raw_attribute in raw_response.get("data", [])
        ]

    @staticmethod
    def build_device_detailed_information_obj(
        raw_response: Dict, api_root: Optional[str] = None
    ) -> DeviceDetailedInformation:
        raw_response = raw_response.get("data", {})
        adapters = AxoniusTransformationLayer.build_device_detailed_information_adapters_obj_list(
            raw_response.get("attributes", {}).get("adapters", [])
        )
        return DeviceDetailedInformation(
            raw_data=raw_response,
            internal_axon_id=raw_response.get("attributes", {}).get("internal_axon_id"),
            labels=raw_response.get("attributes", {}).get("labels", []),
            api_root=api_root,
            adapters=adapters,
            notes=AxoniusTransformationLayer.build_device_detailed_information_notes_obj_list(
                raw_response
            ),
        )

    @staticmethod
    def build_device_detailed_information_adapters_obj_list(
        raw_adapters: List[Dict],
    ) -> List[DeviceDetailedInformation.Adapter]:
        return [
            AxoniusTransformationLayer.build_device_detailed_information_adapter_obj(
                raw_adapter
            )
            for raw_adapter in raw_adapters
        ]

    @staticmethod
    def build_device_detailed_information_adapter_obj(
        raw_adapter: Dict,
    ) -> DeviceDetailedInformation.Adapter:
        network_interfaces = (
            raw_adapter.get("data", {}).get("raw", {}).get("network_interfaces", [])
        )
        if network_interfaces:
            ips = network_interfaces[0].get("ips")
        else:
            ips = None
        raw_os = raw_adapter.get("data", {}).get("raw", {}).get("os", {})
        raw_os_str = raw_os if isinstance(raw_os, str) else raw_os.get("os_str")
        data_os = raw_adapter.get("data", {}).get("os", {})
        os_str = data_os if isinstance(data_os, str) else data_os.get("os_str")

        return DeviceDetailedInformation.Adapter(
            raw_data=raw_adapter,
            data_raw=raw_adapter.get("data", {}).get("raw"),
            plugin_name=raw_adapter.get("plugin_name"),
            plugin_type=raw_adapter.get("plugin_type"),
            adapter_type=raw_adapter.get("type"),
            object_classes=raw_adapter.get("data", {})
            .get("raw", {})
            .get("ad_object_class", []),
            site_name=raw_adapter.get("data", {}).get("raw", {}).get("ad_site_name"),
            device_disabled=raw_adapter.get("data", {})
            .get("raw", {})
            .get("device_disabled"),
            device_managed_by=raw_adapter.get("data", {})
            .get("raw", {})
            .get("device_managed_by"),
            hostname=raw_adapter.get("data", {}).get("raw", {}).get("hostname"),
            ad_distinguished_name=raw_adapter.get("data", {})
            .get("raw", {})
            .get("ad_distinguished_name"),
            asset_name=raw_adapter.get("data", {}).get("raw", {}).get("name"),
            ips=ips,
            os=raw_os_str if raw_os_str else os_str,
        )

    @staticmethod
    def build_device_detailed_information_notes_obj_list(
        raw_response: Dict,
    ) -> List[DeviceDetailedInformation.Note]:
        attributes_data = raw_response.get("attributes", {}).get("data", [])
        if attributes_data:
            return [
                AxoniusTransformationLayer.build_device_detailed_information_note_obj(
                    raw_note
                )
                for raw_note in attributes_data[0].get("data", [])
            ]

    @staticmethod
    def build_device_detailed_information_note_obj(
        raw_note: Dict,
    ) -> DeviceDetailedInformation.Note:
        return DeviceDetailedInformation.Note(
            raw_data=raw_note,
            accurate_for_datetime=raw_note.get("accurate_for_datetime"),
            note=raw_note.get("note"),
            user_name=raw_note.get("user_name"),
            user_id=raw_note.get("user_id"),
        )

    @staticmethod
    def build_user_note_obj(raw_note: Dict) -> UserNote:
        return UserNote(
            raw_data=raw_note,
            accurate_for_datetime=raw_note.get("data", {})
            .get("attributes", {})
            .get("accurate_for_datetime"),
            note=raw_note.get("data", {}).get("attributes", {}).get("note"),
            user_id=raw_note.get("data", {}).get("attributes", {}).get("user_id"),
            user_name=raw_note.get("data", {}).get("attributes", {}).get("user_name"),
        )

    @staticmethod
    def build_device_note_obj(raw_note: Dict) -> DeviceNote:
        return DeviceNote(
            raw_data=raw_note,
            accurate_for_datetime=raw_note.get("data", {})
            .get("attributes", {})
            .get("accurate_for_datetime"),
            note=raw_note.get("data", {}).get("attributes", {}).get("note"),
            user_id=raw_note.get("data", {}).get("attributes", {}).get("user_id"),
            user_name=raw_note.get("data", {}).get("attributes", {}).get("user_name"),
        )
