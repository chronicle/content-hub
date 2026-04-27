from __future__ import annotations
from .datamodels import *


class McAfeeMvisionEDRV2Parser:
    def get_auth_token(self, raw_json):
        return f'{raw_json.get("token_type", "")} {raw_json.get("access_token", "")}'

    def build_siemplify_investigation(self, investigation_json):
        return Investigation(
            raw_data=investigation_json,
            name=investigation_json.get("attributes", {}).get("name"),
            owner=investigation_json.get("attributes", {}).get("owner"),
            created=investigation_json.get("attributes", {}).get("created"),
            investigation_id=investigation_json.get("id"),
            summary=investigation_json.get("attributes", {}).get("summary"),
            last_modified=investigation_json.get("attributes", {}).get("lastModified"),
            is_automatic=investigation_json.get("attributes", {}).get("isAutomatic"),
            hint=investigation_json.get("attributes", {}).get("hint"),
            case_type=investigation_json.get("attributes", {}).get("caseType"),
            investigated=investigation_json.get("attributes", {}).get("investigated"),
            status=investigation_json.get("attributes", {}).get("status"),
            priority=investigation_json.get("attributes", {}).get("priority"),
        )
