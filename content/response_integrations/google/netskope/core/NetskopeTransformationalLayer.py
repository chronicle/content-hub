from __future__ import annotations
from .datamodels import Client, User


class NetskopeTransformationalLayer:

    def build_siemplify_client(self, client_json):
        return Client(
            raw_data=client_json.get("attributes"),
            device_id=client_json.get("attributes", {}).get("_id"),
            os=client_json.get("attributes", {}).get("host_info", {}).get("os"),
            users=[
                self.build_siemplify_users(users_json).username
                for users_json in client_json.get("attributes", {}).get("users", [])
            ],
        )

    def build_siemplify_users(self, users_json):
        return User(raw_data=users_json, username=users_json.get("username"))
