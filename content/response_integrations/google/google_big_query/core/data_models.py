from __future__ import annotations

import dataclasses

from TIPCommon.types import SingleJson


@dataclasses.dataclass
class WorkloadIdentityConfiguration:
    api_root: str | None
    user_service_account: SingleJson | None
    service_account_fields: GoogleServiceAccount
    workload_identity_email: str
    quota_project_id: str
    verify_ssl: bool


@dataclasses.dataclass
class GoogleServiceAccount:
    account_type: str | None
    project_id: str | None
    private_key_id: str | None
    private_key: str | None
    client_email: str | None
    client_id: str | None
    auth_uri: str | None
    token_uri: str | None
    auth_provider_x509_url: str | None
    client_x509_cert_url: str | None

    def to_json(self) -> dict[str, str | None]:
        return {
            "account_type": self.account_type,
            "project_id": self.project_id,
            "private_key_id": self.private_key_id,
            "private_key": self.private_key,
            "client_email": self.client_email,
            "client_id": self.client_id,
            "auth_uri": self.auth_uri,
            "token_uri": self.token_uri,
            "client_x509_cert_url": self.client_x509_cert_url,
            "auth_provider_x509_url": self.auth_provider_x509_url,
        }
