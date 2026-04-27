from __future__ import annotations
from .datamodels import *


class F5BIGIPAccessPolicyManagerParser:

    @staticmethod
    def build_active_sessions_object(raw_data):
        active_session_data = raw_data.get("entries", {})

        return [
            ActiveSessionObject(
                raw_data=raw_data,
                active_session_id=active_session_key.split("/")[-1],
                stats=active_session_value.get("nestedStats"),
                client_ip=active_session_value.get("nestedStats", {})
                .get("entries", {})
                .get("clientIp", {})
                .get("description"),
                logon_user=active_session_value.get("nestedStats", {})
                .get("entries", {})
                .get("logonUser", {})
                .get("description"),
            )
            for active_session_key, active_session_value in active_session_data.items()
        ]
