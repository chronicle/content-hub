# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
from .datamodels import *


class SonicWallParser:
    def build_response_object(self, response_json):
        return ResponseObject(
            raw_data=response_json,
            command=response_json.get("status", {}).get("cli", {}).get("command"),
            message=response_json.get("status", {}).get("info", [])[0].get("message"),
            code=response_json.get("status", {}).get("info", [])[0].get("code"),
        )

    def build_ip_object(self, response_json):
        return IPObject(
            raw_data=response_json,
            name=response_json.get("name"),
            uuid=response_json.get("uuid"),
            zone=response_json.get("zone"),
            ip=response_json.get("host", {}).get("ip"),
        )

    def build_address_group(self, response_json, ip_type):
        return AddressGroup(
            raw_data=response_json,
            name=response_json.get("name"),
            uuid=response_json.get("uuid"),
            address_objects=[
                self.build_ip_object(ip_object)
                for ip_object in response_json.get("address_object", {}).get(
                    ip_type, []
                )
            ],
        )

    def build_uri_list_object(self, response_json):
        return URIListObject(
            raw_data=response_json,
            name=response_json.get("name"),
            uri_list=[
                self.build_uri_object(uri_object)
                for uri_object in response_json.get("uri", [])
            ],
        )

    def build_uri_object(self, response_json):
        return URIObject(raw_data=response_json, uri=response_json.get("uri"))

    def build_uri_list_group_object(self, response_json):
        return URIListGroupObject(
            raw_data=response_json, name=response_json.get("name")
        )

    def build_uri_list(self, response_json):
        return URIListGroupObject(
            raw_data=response_json, name=response_json.get("name")
        )

    def build_uri_group_object(self, response_json):
        return URIGroupObject(
            raw_data=response_json,
            name=response_json.get("name"),
            uri_list=[
                self.build_uri_list_group_object(uri_object)
                for uri_object in response_json.get("uri_list_object", [])
            ],
            uri_group=[
                self.build_uri_list(uri_object)
                for uri_object in response_json.get("uri_list_group", [])
            ],
        )
