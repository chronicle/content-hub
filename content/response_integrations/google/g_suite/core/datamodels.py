from __future__ import annotations

import collections
import dataclasses

from TIPCommon.transformation import dict_to_flat, add_prefix_to_dict
from TIPCommon.types import SingleJson

from g_suite.core.consts import ENRICHMENT_PREFIX

IntegrationParameters = collections.namedtuple(
    "IntegrationParameters", ["siemplify_logger"]
)


@dataclasses.dataclass(slots=True)
class BaseModel:
    raw_data: SingleJson

    def to_json(self) -> SingleJson:
        return self.raw_data

    def as_json(self) -> SingleJson:
        """
        Provides backward compatibility with code expecting an as_json method.
        """
        return self.raw_data


class OrgUnit(dict):
    """
    GSuite Organization unit datamodel
    """

    def __init__(self, raw_data, **kwargs):
        super().__init__(raw_data)
        self.raw_data = raw_data
        self.kind = kwargs.get("kind")
        self.name = kwargs.get("name")
        self.description = kwargs.get("description")
        self.etag = kwargs.get("etag")
        self.block_inheritance = kwargs.get("blockInheritance")
        self.org_unit_id = kwargs.get("orgUnitId")
        self.org_unit_path = kwargs.get("orgUnitPath")
        self.parent_org_unit_id = kwargs.get("parentOrgUnitId")
        self.parent_org_unit_path = kwargs.get("parentOrgUnitPath")

    def as_json(self):
        return self.raw_data

    def as_csv(self):
        return {
            "Kind": self.kind,
            "Name": self.name,
            "Description": self.description,
            "Etag": self.etag,
            "Block Inheritance": self.block_inheritance,
            "Org Unit Id": self.org_unit_id,
            "Org Unit Path": self.org_unit_path,
            "Parent Org Unit Id": self.parent_org_unit_id,
            "Parent Org Unit Path": self.parent_org_unit_path,
        }


class Group:
    """
    GSuite Group data model
    """

    def __init__(self, raw_data, **kwargs):
        self.raw_data = raw_data
        self.id = kwargs.get("id")
        self.email = kwargs.get("email")
        self.name = kwargs.get("name")
        self.description = kwargs.get("description")
        self.admin_created = kwargs.get("adminCreated")
        self.direct_member_count = kwargs.get("directMembersCount")
        self.kind = kwargs.get("kind")
        self.etag = kwargs.get("etag")
        self.aliases = kwargs.get("aliases", [])
        self.non_editable_aliases = kwargs.get("nonEditableAliases", [])

    def as_json(self):
        return self.raw_data


class User:
    """
    GSuite user data model.
    """

    class Phone:
        """
        GSuite phone data model
        """

        def __init__(self, value=None, type=None, is_primary=None):
            self.value = value
            self.type = type
            self.is_primary = is_primary

    def __init__(self, raw_data, **kwargs):
        self.raw_data = raw_data
        self.id = kwargs.get("id")
        self.kind = kwargs.get("kind")
        self.etag = kwargs.get("etag")
        self.email = kwargs.get("primaryEmail")
        self.given_name = kwargs.get("given_name")
        self.family_name = kwargs.get("family_name")
        self.is_admin = kwargs.get("isAdmin")
        self.creation_time = kwargs.get("creationTime")
        self.phones = kwargs.get("phones_objs", [])
        self.gender = kwargs.get("gender_type")
        self.is_delegated_admin = kwargs.get("isDelegatedAdmin")
        self.last_login_time = kwargs.get("lastLoginTime")
        self.is_account_suspended = kwargs.get("suspended")
        self.is_account_archived = kwargs.get("archived")
        self.change_password_at_next_login = kwargs.get("changePasswordAtNextLogin")
        self.customer_id = kwargs.get("customerId")
        self.org_unit_path = kwargs.get("orgUnitPath")
        self.is_mailbox_setup = kwargs.get("isMailboxSetup")
        self.recovery_email = kwargs.get("recoveryEmail")

    def as_json(self):
        return self.raw_data

    def as_enriched(self):
        return add_prefix_to_dict(dict_to_flat(self.raw_data), ENRICHMENT_PREFIX)

    def as_csv(self):
        return {
            "Id": self.id,
            "Email": self.email,
            "Given Name": self.given_name,
            "Family Name": self.family_name,
            "Is Admin?": self.is_admin,
            "Is Delegated Admin?": self.is_delegated_admin,
            "Creation Time": self.creation_time,
            "Last Login Time": self.last_login_time,
            "Suspended?": self.is_account_suspended,
            "Archived?": self.is_account_archived,
            "Change Password At Next Login?": self.change_password_at_next_login,
            "Customer ID": self.customer_id,
            "Org Unit Path": self.org_unit_path,
            "Is Mailbox set?": self.is_mailbox_setup,
            "Recovery Email": self.recovery_email,
        }


class Member:
    """
    GSuite group member data model
    """

    def __init__(self, raw_data=None, **kwargs):
        self.raw_data = raw_data
        self.kind = kwargs.get("kind")
        self.email = kwargs.get("email")
        self.role = kwargs.get("role")
        self.etag = kwargs.get("etag")
        self.type = kwargs.get("type")
        self.status = kwargs.get("status")
        self.delivery_settings = kwargs.get("delivery_settings")
        self.id = kwargs.get("id")

    def as_json(self):
        return self.raw_data

    def as_csv(self):
        return {
            "kind": self.kind,
            "email": self.email,
            "role": self.role,
            "etag": self.etag,
            "type": self.type,
            "status": self.status,
            "delivery_settings": self.delivery_settings,
            "id": self.id,
        }


class Role:
    """
    Gsuite Role data model
    """

    def __init__(self, raw_data=None, **kwargs) -> None:
        self.raw_data = raw_data
        self.role_id = kwargs.get("roleId")
        self.role_name = kwargs.get("roleName")
        self.role_privileges = kwargs.get("rolePrivileges")

    def as_json(self):
        return self.raw_data


class RoleAssignment:
    """
    Gsuite Role Assignment data model
    """

    def __init__(self, raw_data=None, **kwargs) -> None:
        self.raw_data = raw_data
        self.role_id = kwargs.get("roleId")

    def as_json(self):
        return self.raw_data


class GroupsSettings:
    """
    GSuite representation of GroupSettings
    """

    def __init__(self, raw_data=None):
        self.raw_data = raw_data

    def as_json(self):
        return self.raw_data


class AccessToken:
    """
    Gsuite access token
    """

    def __init__(self, raw_data, access_token, token_type, **kwargs):
        self.raw_data = raw_data
        self.access_token = access_token
        self.token_type = token_type


@dataclasses.dataclass(slots=True)
class UserActivityEvent(BaseModel):
    """
    Data model for a GSuite User Activity Event.
    """
    kind: str | None = None
    id: SingleJson = dataclasses.field(default_factory=dict)
    etag: str | None = None
    actor: SingleJson = dataclasses.field(default_factory=dict)
    ip_address: str | None = None
    events: list[SingleJson] = dataclasses.field(default_factory=list)

    @classmethod
    def from_json(cls, event_json: SingleJson) -> UserActivityEvent:
        return cls(
            raw_data=event_json,
            kind=event_json.get("kind"),
            id=event_json.get("id", {}),
            etag=event_json.get("etag"),
            actor=event_json.get("actor", {}),
            ip_address=event_json.get("ipAddress"),
            events=event_json.get("events", []),
        )


@dataclasses.dataclass(slots=True)
class Browser(BaseModel):
    """
    Represents a Chrome browser device in Google Workspace.
    """
    browser_id: str | None = None
    machine_name: str | None = None
    os_platform: str | None = None
    os_version: str | None = None
    last_activity_time: str | None = None

    @classmethod
    def from_json(cls, browser_json: SingleJson) -> Browser:
        return cls(
            raw_data=browser_json,
            browser_id=browser_json.get("browserId"),
            machine_name=browser_json.get("machineName"),
            os_platform=browser_json.get("osPlatform"),
            os_version=browser_json.get("osVersion"),
            last_activity_time=browser_json.get("lastActivityTime"),
        )

    def as_csv(self) -> SingleJson:
        return {
            "Browser ID": self.browser_id,
            "Machine Name": self.machine_name,
            "OS Platform": self.os_platform,
            "OS Version": self.os_version,
            "Last Activity": self.last_activity_time,
        }


@dataclasses.dataclass(slots=True)
class ExtensionDetails(BaseModel):
    """
    Data model for Chrome Extension details.
    """
    app_id: str | None = None
    display_name: str | None = None
    description: str | None = None
    type: str | None = None
    homepage_uri: str | None = None

    @classmethod
    def from_json(cls, extension_json: SingleJson) -> ExtensionDetails:
        return cls(
            raw_data=extension_json,
            app_id=extension_json.get("appId"),
            display_name=extension_json.get("displayName"),
            description=extension_json.get("description"),
            type=extension_json.get("type"),
            homepage_uri=extension_json.get("homepageUri"),
        )


@dataclasses.dataclass(slots=True)
class RequestingUser(BaseModel):
    """
    Data model for a user requesting an extension.
    """
    user_email: str | None = None
    justification: str | None = None

    @classmethod
    def from_json(cls, user_json: SingleJson) -> RequestingUser:
        return cls(
            raw_data=user_json,
            user_email=user_json.get("email"),
            justification=user_json.get("justification"),
        )


@dataclasses.dataclass(slots=True)
class RequestingDevice(BaseModel):
    """
    Data model for a device requesting an extension.
    """
    device_name: str | None = None
    justification: str | None = None

    @classmethod
    def from_json(cls, device_json: SingleJson) -> RequestingDevice:
        return cls(
            raw_data=device_json,
            device_name=device_json.get("deviceName"),
            justification=device_json.get("justification"),
        )


@dataclasses.dataclass(slots=True)
class ResolvedPolicy(BaseModel):
    """
    Data model for a resolved policy object from the Chrome Policy API.
    """
    target_key: SingleJson = dataclasses.field(default_factory=dict)
    value: SingleJson = dataclasses.field(default_factory=dict)
    source_key: SingleJson = dataclasses.field(default_factory=dict)
    added_source_key: SingleJson = dataclasses.field(default_factory=dict)

    @classmethod
    def from_json(cls, policy_json: SingleJson) -> ResolvedPolicy:
        return cls(
            raw_data=policy_json,
            target_key=policy_json.get("targetKey", {}),
            value=policy_json.get("value", {}),
            source_key=policy_json.get("sourceKey", {}),
            added_source_key=policy_json.get("addedSourceKey", {}),
        )

    @property
    def install_type(self) -> str | None:
        return self.value.get("value", {}).get("appInstallType")
