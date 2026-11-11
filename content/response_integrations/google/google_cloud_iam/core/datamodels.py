from __future__ import annotations

import copy
from typing import Optional, List

from TIPCommon import dict_to_flat, add_prefix_to_dict
from TIPCommon.types import SingleJson

from google_cloud_iam.core.consts import ENRICHMENT_PREFIX


class BaseModel:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_flat(self):
        return dict_to_flat(self.to_json())

    def to_table(self):
        return [self.to_csv()]

    def to_csv(self):
        return dict_to_flat(self.to_json())

    def is_empty(self):
        return not bool(self.raw_data)


class Policy(BaseModel):
    """
    IAM Policy data model
    """

    class Binding(BaseModel):
        """
        Policy binding data model
        """

        def __init__(
            self,
            raw_data: dict,
            role: Optional[str] = None,
            members: Optional[List[str]] = None,
        ):
            super(Policy.Binding, self).__init__(raw_data)
            self.role = role
            self.members = members or []

    def __init__(
        self,
        raw_data: dict,
        etag: Optional[str] = None,
        version: Optional[str] = None,
        bindings: Optional[Binding] = None,
    ):
        super(Policy, self).__init__(raw_data)
        self.etag = etag
        self.version = version
        self.bindings = bindings or []

    def to_enrichment(self, prefix=ENRICHMENT_PREFIX):
        enrichment_table = {"version": self.version}
        for binding in self.bindings:
            enrichment_table.update(
                {f"bindings_role_{binding.role}": ", ".join(binding.members)}
            )
        return add_prefix_to_dict(dict_to_flat(enrichment_table), prefix)


class Role(BaseModel):
    """
    IAM Role data model
    """

    def __init__(
        self,
        raw_data: dict,
        name: Optional[str] = None,
        stage: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        etag: Optional[str] = None,
        permissions: Optional[List[str]] = None,
    ):
        super(Role, self).__init__(raw_data)
        self.name = name
        self.title = title
        self.stage = stage
        self.description = description
        self.etag = etag
        self.permissions = permissions or []

    def to_csv(self):
        csv_table = {
            "Role Name": self.name,
            "Role Title": self.title,
            "Role Stage": self.stage,
            "Role Description": self.description,
            "Role Etag": self.etag,
        }
        if self.permissions:
            csv_table.update({"Rule Permissions": ", ".join(self.permissions)})
        return csv_table

    def to_json(self):
        data = copy.deepcopy(self.raw_data)
        if isinstance(self.name, str):
            data["role_id"] = self.name.split("/")[-1]
        return data


class ServiceAccount(BaseModel):
    """
    Service Account data model
    """

    def __init__(
        self,
        raw_data: dict,
        name: Optional[str] = None,
        unique_id: Optional[str] = None,
        email: Optional[str] = None,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        oath_2_client_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ):
        super(ServiceAccount, self).__init__(raw_data)
        self.name = name
        self.unique_id = unique_id
        self.email = email or ""
        self.display_name = display_name or ""
        self.description = description
        self.oath_2_client_id = oath_2_client_id
        self.project_id = project_id

    def to_csv(self):
        csv_table = {
            f"Name": self.name or "",
            f"Unique ID": self.unique_id or "",
            f"Email": self.email,
            f"Display Name": self.display_name,
            f"Description": self.description or "",
            f"Oauth2 Client ID": self.oath_2_client_id or "",
        }
        return csv_table

    def to_enrichment(self, prefix=ENRICHMENT_PREFIX):
        enrichment_table = {
            "name": self.name,
            "project_id": self.project_id,
            "unique_id": self.unique_id,
            "email": self.email,
            "display_name": self.display_name,
            "description": self.description,
            "oauth2_client_id": self.oath_2_client_id,
        }
        return add_prefix_to_dict(dict_to_flat(enrichment_table), prefix)


class ServiceAccountKey(BaseModel):
    """
    Service Account Key data model
    """

    def __init__(
        self,
        raw_data: SingleJson,
        name: str,
        valid_after_time: str,
        valid_before_time: str,
        key_algorithm: str,
        key_origin: str,
        key_type: str,
        private_key_data: str | None = None,
    ) -> None:
        super().__init__(raw_data)
        self.name = name
        self.valid_after_time = valid_after_time
        self.valid_before_time = valid_before_time
        self.key_algorithm = key_algorithm
        self.key_origin = key_origin
        self.key_type = key_type
        self.private_key_data = private_key_data

    def to_json(self) -> SingleJson:
        data = {
            "name": self.name,
            "validAfterTime": self.valid_after_time,
            "validBeforeTime": self.valid_before_time,
            "keyAlgorithm": self.key_algorithm,
            "keyOrigin": self.key_origin,
            "keyType": self.key_type,
        }

        if self.private_key_data:
            data["privateKeyData"] = self.private_key_data

        return data
