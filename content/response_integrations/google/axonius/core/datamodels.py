from __future__ import annotations
import copy
from typing import List, Dict, Optional

from TIPCommon import dict_to_flat, add_prefix_to_dict

from .consts import (
    AXONIUS_ENRICHMENT_PREFIX,
    USER_INSIGHT_TEMPLATE,
    DEVICE_INSIGHT_TEMPLATE,
    HTML_LINK,
    NOT_ASSIGNED,
)
from .utils import remove_none_dictionary_values


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data: Dict):
        self.raw_data = raw_data

    def as_json(self) -> Dict:
        return self.raw_data

    def as_csv(self) -> Dict:
        return dict_to_flat(self.as_json())

    def as_enrichment(self, prefix=AXONIUS_ENRICHMENT_PREFIX) -> Dict:
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class EntityGeneralAttribute(BaseModel):
    def __init__(self, raw_data: Dict):
        super(EntityGeneralAttribute, self).__init__(raw_data)


class UserGeneralAttribute(EntityGeneralAttribute):
    """
    User entity general attribute data model
    """

    def __init__(
        self,
        raw_data: Dict,
        internal_axon_id: Optional[str] = None,
        usernames: Optional[str] = None,
        emails: Optional[str] = None,
        display_names: Optional[str] = None,
    ):
        super(UserGeneralAttribute, self).__init__(raw_data)
        self.internal_axon_id: str = internal_axon_id
        self.usernames: str = usernames
        self.emails: str = emails
        self.display_names: str = display_names


class DeviceGeneralAttribute(EntityGeneralAttribute):
    """
    Device entity general attribute data model
    """

    def __init__(
        self,
        raw_data: Dict,
        internal_axon_id: Optional[str] = None,
        ips: Optional[List[str]] = None,
        macs: Optional[List[str]] = None,
        name: Optional[str] = None,
        hostname: Optional[str] = None,
    ):
        super(DeviceGeneralAttribute, self).__init__(raw_data)
        self.internal_axon_id: str = internal_axon_id
        self.ips: List[str] = ips or []
        self.macs: List[str] = macs or []
        self.name: str = name
        self.hostname: str = hostname


class UserDetailedInformation(BaseModel):
    """
    Detailed user information data model
    """

    class Note(BaseModel):
        """
        User notes data model
        """

        def __init__(
            self,
            raw_data: Dict,
            accurate_for_datetime: Optional[str] = None,
            note: Optional[str] = None,
            user_name: Optional[str] = None,
            user_id: Optional[str] = None,
        ):
            super(UserDetailedInformation.Note, self).__init__(raw_data)
            self.accurate_for_datetime: str = accurate_for_datetime
            self.note: str = note
            self.user_name: str = user_name
            self.user_id: str = user_id

        def as_csv(self):
            return {
                "Username": self.user_name,
                "Note": self.note,
                "Time": self.accurate_for_datetime,
            }

    class Adapter(BaseModel):
        """
        User adapter connection data model
        """

        def __init__(
            self,
            raw_data: Dict,
            adapter_type: Optional[str] = None,
            data_raw: Optional[Dict] = None,
        ):
            super(UserDetailedInformation.Adapter, self).__init__(raw_data)
            self.adapter_type: str = adapter_type
            self.data_raw: Dict = data_raw

        def as_json(self) -> Dict:
            json_results = copy.deepcopy(self.raw_data)
            json_results.pop("data", None)
            if self.data_raw:
                json_results["raw"] = self.data_raw
            return json_results

        @property
        def is_entity_data_adapter(self) -> bool:
            """
            Check if adapter contains entity data
            :return: {bool} True if adapter of entity data type, otherwise False
            """
            return bool(self.adapter_type == "entitydata")

        @property
        def ignore_adapter_json_results(self) -> bool:
            """
            Check if adapter should be ignored for json results
            :return: {bool} True if no json results should be created from the user, Otherwise False
            """
            return not bool(self.adapter_type == "entitydata")

    def __init__(
        self,
        raw_data: Dict,
        internal_axon_id: Optional[str] = None,
        labels: Optional[List[str]] = None,
        account_disabled: Optional[bool] = None,
        ad_display_name: Optional[str] = None,
        ad_distinguished_name: Optional[str] = None,
        ad_sid: Optional[str] = None,
        employee_id: Optional[str] = None,
        is_admin: Optional[bool] = None,
        is_local: Optional[bool] = None,
        is_locked: Optional[bool] = None,
        mail: Optional[str] = None,
        user_telephone_number: Optional[str] = None,
        username: Optional[str] = None,
        display_name: Optional[str] = None,
        api_root: Optional[str] = None,
        notes: Optional[List[Note]] = None,
        adapters: List[Adapter] = None,
    ):
        super(UserDetailedInformation, self).__init__(raw_data)
        self.internal_axon_id: str = internal_axon_id
        self.labels: List[str] = labels or []
        self.account_disabled: bool = account_disabled
        self.ad_display_name: str = ad_display_name
        self.ad_distinguished_name: str = ad_distinguished_name
        self.ad_sid: str = ad_sid
        self.employee_id: str = employee_id
        self.is_admin: bool = is_admin
        self.is_local: bool = is_local
        self.is_locked: bool = is_locked
        self.mail: str = mail
        self.user_telephone_number: str = user_telephone_number

        self.username: str = username
        self.display_name: str = display_name

        self.link: str = (
            f"{api_root}/users/{internal_axon_id}"
            if api_root and internal_axon_id
            else ""
        )

        self.notes: List[UserDetailedInformation.Note] = notes or []
        self.adapters: List[UserDetailedInformation.Adapter] = adapters or []

    @property
    def case_wall_report_link(self):
        return self.link

    def as_enrichment(self, prefix=AXONIUS_ENRICHMENT_PREFIX) -> Dict:
        enrichment_table = add_prefix_to_dict(
            dict_to_flat(
                remove_none_dictionary_values(
                    **{
                        "account_disabled": self.account_disabled,
                        "ad_display_name": self.ad_display_name,
                        "ad_distinguished_name": self.ad_distinguished_name,
                        "ad_sid": self.ad_sid,
                        "employee_id": self.employee_id,
                        "is_admin": self.is_admin,
                        "is_local": self.is_local,
                        "is_locked": self.is_locked,
                        "mail": self.mail,
                        "user_telephone_number": self.user_telephone_number,
                        "id": self.internal_axon_id,
                        "link": self.link or None,
                    }
                )
            ),
            prefix,
        )
        return enrichment_table

    def get_notes_as_csv(self) -> List[Dict]:
        return [note.as_csv() for note in self.notes]

    def as_enrichment_csv_table(self) -> Dict:
        entity_table = dict_to_flat(
            remove_none_dictionary_values(
                **{
                    "account_disabled": self.account_disabled,
                    "ad_distinguished_name": self.ad_distinguished_name,
                    "ad_sid": self.ad_sid,
                    "employee_id": self.employee_id,
                    "is_admin": self.is_admin,
                    "is_local": self.is_local,
                    "is_locked": self.is_locked,
                    "mail": self.mail,
                    "user_telephone_number": self.user_telephone_number,
                    "id": self.internal_axon_id,
                    "link": self.link or None,
                }
            )
        )
        return [{"Key": key, "Value": value} for key, value in entity_table.items()]

    def as_json(self, max_notes_to_return: Optional[int] = None) -> Dict:
        json_results = {
            "adapters": [
                adapter.as_json()
                for adapter in self.adapters
                if not adapter.ignore_adapter_json_results
            ],
            "internal_axon_id": self.internal_axon_id,
            "labels": self.labels,
        }
        if max_notes_to_return:
            json_results["notes"] = [note.as_json() for note in self.notes][
                -max_notes_to_return:
            ]
        return json_results

    def as_insight(self, entity_identifier: str) -> str:
        return USER_INSIGHT_TEMPLATE.format(
            entity_identifier=entity_identifier,
            display_name=self.display_name,
            username=self.username or NOT_ASSIGNED,
            mail=self.mail or NOT_ASSIGNED,
            user_telephone_number=self.user_telephone_number,
            is_admin=self.is_admin if isinstance(self.is_admin, bool) else NOT_ASSIGNED,
            is_local=self.is_local if isinstance(self.is_local, bool) else NOT_ASSIGNED,
            is_locked=(
                self.is_locked if isinstance(self.is_locked, bool) else NOT_ASSIGNED
            ),
            account_disabled=(
                self.account_disabled
                if isinstance(self.account_disabled, bool)
                else NOT_ASSIGNED
            ),
            html_report_link=HTML_LINK.format(link=self.link),
        )


class DeviceDetailedInformation(BaseModel):
    """
    Detailed device information data model
    """

    class Note(BaseModel):
        """
        Device notes data model
        """

        def __init__(
            self,
            raw_data: Dict,
            accurate_for_datetime: Optional[str] = None,
            note: Optional[str] = None,
            user_name: Optional[str] = None,
            user_id: Optional[str] = None,
        ):
            super(DeviceDetailedInformation.Note, self).__init__(raw_data)
            self.accurate_for_datetime: str = accurate_for_datetime
            self.note: str = note
            self.user_name: str = user_name
            self.user_id: str = user_id

        def as_csv(self):
            return {
                "Username": self.user_name,
                "Note": self.note,
                "Time": self.accurate_for_datetime,
            }

    class Adapter(BaseModel):
        """
        Device adapter connection data model
        """

        def __init__(
            self,
            raw_data: Dict,
            adapter_type: Optional[str] = None,
            data_raw: Optional[Dict] = None,
            plugin_name: Optional[str] = None,
            plugin_type: Optional[str] = None,
            object_classes: Optional[List[str]] = None,
            site_name: Optional[str] = None,
            device_disabled: Optional[bool] = None,
            device_managed_by: Optional[str] = None,
            hostname: Optional[str] = None,
            ad_distinguished_name: Optional[str] = None,
            asset_name: Optional[str] = None,
            ips: Optional[List[str]] = None,
            os: Optional[str] = None,
        ):
            super(DeviceDetailedInformation.Adapter, self).__init__(raw_data)
            self.adapter_type: str = adapter_type
            self.data_raw: Dict = data_raw
            self.plugin_name: str = plugin_name
            self.plugin_type: Optional[str] = plugin_type
            self.object_classes: Optional[List[str]] = object_classes or []
            self.site_name: str = site_name
            self.device_disabled: bool = device_disabled
            self.device_managed_by: str = device_managed_by
            self.hostname: str = hostname
            self.ad_distinguished_name: str = ad_distinguished_name
            self.asset_name: str = asset_name
            self.ips: Optional[List[str]] = ips or []
            self.os: str = os

        def as_json(self) -> Dict:
            json_results = copy.deepcopy(self.raw_data)
            json_results.pop("data", None)
            if self.data_raw:
                json_results["raw"] = self.data_raw
            return json_results

        @property
        def is_results_data_adapter(self) -> bool:
            """
            Check if adapter of type to include in entity enrichment
            :return: {bool} True if adapter data to include in entity enrichment data, otherwise False
            """
            return bool(self.plugin_type == "Adapter")

        @property
        def ignore_adapter_json_results(self) -> bool:
            """
            Check if adapter should be ignored for json results
            :return: {bool} True if no json results should be created from the user, Otherwise False
            """
            return not bool(self.adapter_type == "entitydata")

    def __init__(
        self,
        raw_data: Dict,
        internal_axon_id: Optional[str] = None,
        labels: Optional[List[str]] = None,
        api_root: Optional[str] = None,
        notes: Optional[List[Note]] = None,
        adapters: Optional[List[Adapter]] = None,
    ):
        super(DeviceDetailedInformation, self).__init__(raw_data)
        self.internal_axon_id: str = internal_axon_id
        self.labels: List[str] = labels or []
        self.link = (
            f"{api_root}/devices/{internal_axon_id}"
            if api_root and internal_axon_id
            else ""
        )

        self.notes: List[DeviceDetailedInformation.Note] = notes or []
        self.adapters: List[DeviceDetailedInformation.Adapter] = adapters or []

        # Find adapter for enrichment results data
        self.results_data_adapter = next(
            filter(lambda adapter: adapter.is_results_data_adapter, adapters), None
        )

    @property
    def case_wall_report_link(self):
        return self.link

    def as_enrichment(self, prefix=AXONIUS_ENRICHMENT_PREFIX) -> Dict:
        enrichment_table = dict()
        if self.results_data_adapter:

            ad_object_classes: Optional[str] = None
            ad_ips: Optional[str] = None
            if self.results_data_adapter.object_classes:
                ad_object_classes = ", ".join(self.results_data_adapter.object_classes)
            if self.results_data_adapter.ips:
                ad_ips = ", ".join(self.results_data_adapter.ips)

            enrichment_table = add_prefix_to_dict(
                dict_to_flat(
                    remove_none_dictionary_values(
                        **{
                            "object_classes": ad_object_classes,
                            "site_name": self.results_data_adapter.site_name,
                            "device_disabled": self.results_data_adapter.device_disabled,
                            "device_managed_by": self.results_data_adapter.device_managed_by,
                            "hostname": self.results_data_adapter.hostname,
                            "ad_distinguished_name": self.results_data_adapter.ad_distinguished_name,
                            "asset_name": self.results_data_adapter.asset_name,
                            "ips": ad_ips,
                            "os": self.results_data_adapter.os,
                            "id": self.internal_axon_id,
                            "link": self.link,
                        }
                    )
                ),
                prefix,
            )
        return enrichment_table

    def get_notes_as_csv(self) -> List[Dict]:
        return [note.as_csv() for note in self.notes]

    def as_enrichment_csv_table(self) -> Dict:
        if self.results_data_adapter:

            ad_object_classes: Optional[str] = None
            ad_ips: Optional[str] = None
            if self.results_data_adapter.object_classes:
                ad_object_classes = ", ".join(self.results_data_adapter.object_classes)
            if self.results_data_adapter.ips:
                ad_ips = ", ".join(self.results_data_adapter.ips)

            entity_table = dict_to_flat(
                remove_none_dictionary_values(
                    **{
                        "object_classes": ad_object_classes,
                        "site_name": self.results_data_adapter.site_name,
                        "device_disabled": self.results_data_adapter.device_disabled,
                        "device_managed_by": self.results_data_adapter.device_managed_by,
                        "hostname": self.results_data_adapter.hostname,
                        "ad_distinguished_name": self.results_data_adapter.ad_distinguished_name,
                        "asset_name": self.results_data_adapter.asset_name,
                        "ips": ad_ips,
                        "os": self.results_data_adapter.os,
                        "id": self.internal_axon_id,
                        "link": self.link,
                    }
                )
            )
            return [{"Key": key, "Value": value} for key, value in entity_table.items()]

    def as_json(self, max_notes_to_return: Optional[int] = None) -> Dict:
        json_results = {
            "adapters": [
                adapter.as_json()
                for adapter in self.adapters
                if not adapter.ignore_adapter_json_results
            ],
            "internal_axon_id": self.internal_axon_id,
            "labels": self.labels,
        }
        if max_notes_to_return:
            json_results["notes"] = [note.as_json() for note in self.notes][
                -max_notes_to_return:
            ]
        return json_results

    def as_insight(self, entity_identifier: str) -> str:
        if self.results_data_adapter:
            return DEVICE_INSIGHT_TEMPLATE.format(
                entity_identifier=entity_identifier,
                asset_name=self.results_data_adapter.asset_name or NOT_ASSIGNED,
                hostname=self.results_data_adapter.hostname or NOT_ASSIGNED,
                ip_addresses=(
                    ", ".join(self.results_data_adapter.ips)
                    if self.results_data_adapter.ips
                    else NOT_ASSIGNED
                ),
                device_managed_by=self.results_data_adapter.device_managed_by
                or NOT_ASSIGNED,
                os=self.results_data_adapter.os or NOT_ASSIGNED,
                device_disabled=(
                    self.results_data_adapter.device_managed_by
                    if isinstance(self.results_data_adapter.device_disabled, bool)
                    else None
                ),
                html_report_link=HTML_LINK.format(link=self.link),
            )


class UserNote(BaseModel):
    """
    User Note data model
    """

    def __init__(
        self,
        raw_data: Dict,
        accurate_for_datetime: Optional[str] = None,
        note: Optional[str] = None,
        user_name: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        super(UserNote, self).__init__(raw_data)
        self.accurate_for_datetime: str = accurate_for_datetime
        self.note: str = note
        self.user_name: str = user_name
        self.user_id: str = user_id


class DeviceNote(BaseModel):
    """
    Device Note data model
    """

    def __init__(
        self,
        raw_data: Dict,
        accurate_for_datetime: Optional[str] = None,
        note: Optional[str] = None,
        user_name: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        super(DeviceNote, self).__init__(raw_data)
        self.accurate_for_datetime: str = accurate_for_datetime
        self.note: str = note
        self.user_name: str = user_name
        self.user_id: str = user_id
