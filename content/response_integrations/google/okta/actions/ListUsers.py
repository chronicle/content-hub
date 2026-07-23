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
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import construct_csv, dict_to_flat
from ..core.OktaManager import OktaManager
import json


PROVIDER = "Okta"
ACTION_NAME = "Okta - ListUsers"


def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME
    conf = siemplify.get_configuration(PROVIDER)

    api_root = conf.get("Api Root")
    api_token = conf.get("Api Token")
    client_id = conf.get("Client ID")
    use_oauth_authentication = (
        conf.get("Use Oauth Authentication", "false").lower() == "true"
    )
    key_id = conf.get("Key ID")
    private_key = conf.get("Private Key")
    verify_ssl = conf.get("Verify SSL", "false").lower() == "true"

    q = siemplify.parameters.get("Query", "")
    _filter = siemplify.parameters.get("Filter", "")
    search = siemplify.parameters.get("Search", "")
    limit = siemplify.parameters.get("Limit", "")
    output_message = ""
    errors = "\n\nErrors:\n\n"
    if limit:
        try:
            limit = int(limit)
        except:
            raise Exception("Limit must be an integer")

    okta = OktaManager(
        api_root=api_root,
        api_token=api_token,
        client_id=client_id,
        use_oauth_authentication=use_oauth_authentication,
        key_id=key_id,
        private_key=private_key,
        verify_ssl=verify_ssl,
        logger=siemplify.LOGGER,
    )
    users = {}
    try:
        users = okta.list_users(q=q, _filter=_filter, search=search, limit=limit)
    except Exception as err:
        siemplify.LOGGER.exception(err)
        siemplify.LOGGER.error(err)
        errors += err + "\n\n"
        pass
    output_message = "No Users Were Found"
    if users:
        output_message = f"Found {len(users)} users"
        # i = 1
        for i, user in enumerate(users, 1):
            flat_user = dict_to_flat(user)
            csv_output = construct_csv([flat_user])
            siemplify.result.add_data_table(
                "Okta - User " + str(i) + ": " + user["profile"]["login"], csv_output
            )
            # i += 1
    siemplify.end(output_message + errors, json.dumps(users))


if __name__ == "__main__":
    main()
