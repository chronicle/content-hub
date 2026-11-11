from __future__ import annotations

from typing import TYPE_CHECKING

from g_suite.core.datamodels import (
    AccessToken,
    Browser,
    ExtensionDetails,
    Group,
    GroupsSettings,
    OrgUnit,
    Member,
    ResolvedPolicy,
    RequestingUser,
    RequestingDevice,
    Role,
    RoleAssignment,
    UserActivityEvent,
    User,
)

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


class GSuiteParser:
    """
    GSuite parser
    """

    @staticmethod
    def build_ou_obj(raw_data):
        return OrgUnit(raw_data=raw_data, **raw_data)

    @staticmethod
    def build_group_obj(raw_data):
        return Group(raw_data=raw_data, **raw_data)

    @staticmethod
    def build_user_phone_obj(raw_data):
        return User.Phone(
            value=raw_data.get("value"),
            type=raw_data.get("type"),
            is_primary=raw_data.get("primary"),
        )

    @staticmethod
    def build_user_obj(raw_data):
        return User(
            raw_data=raw_data,
            given_name=raw_data.get("name", {}).get("givenName"),
            family_name=raw_data.get("name", {}).get("familyName"),
            phones_objs=[
                GSuiteParser.build_user_phone_obj(phone)
                for phone in raw_data.get("phones", [])
            ],
            gender_type=raw_data.get("gender", {}).get("type"),
            **raw_data
        )

    @staticmethod
    def build_org_units_objs(raw_data):
        return [
            GSuiteParser.build_ou_obj(ou_raw)
            for ou_raw in raw_data.get("organizationUnits", [])
        ]

    @staticmethod
    def build_member_obj(raw_data):
        return Member(raw_data=raw_data, **raw_data)

    @staticmethod
    def build_role_obj(raw_data):
        return Role(raw_data=raw_data, **raw_data)

    @staticmethod
    def build_role_assignment_obj(raw_data):
        return RoleAssignment(raw_data=raw_data, **raw_data)

    @staticmethod
    def build_group_settings_obj(raw_data):
        return GroupsSettings(raw_data=raw_data)

    @staticmethod
    def build_token_obj(raw_data):
        return AccessToken(raw_data=raw_data, **raw_data)

    @staticmethod
    def build_user_activity_event_obj(raw_data: SingleJson) -> UserActivityEvent:
        return UserActivityEvent.from_json(raw_data)

    @staticmethod
    def build_browser_obj(raw_data: SingleJson) -> Browser:
        return Browser.from_json(raw_data)

    @staticmethod
    def build_extension_details_obj(raw_data: SingleJson) -> ExtensionDetails:
        return ExtensionDetails.from_json(raw_data)

    @staticmethod
    def build_requesting_user_obj(raw_data: SingleJson) -> RequestingUser:
        return RequestingUser.from_json(raw_data)

    @staticmethod
    def build_requesting_device_obj(raw_data: SingleJson) -> RequestingDevice:
        return RequestingDevice.from_json(raw_data)

    @staticmethod
    def build_resolved_policies_objs(raw_json: SingleJson) -> list[ResolvedPolicy]:
        return [
            ResolvedPolicy.from_json(policy)
            for policy in raw_json.get("resolvedPolicies", [])
        ]
