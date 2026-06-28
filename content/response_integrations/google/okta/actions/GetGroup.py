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
from okta.core.OktaManager import OktaManager
import json

PROVIDER = "Okta"
ACTION_NAME = "Okta - GetGroup"


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

    group_ids_or_names = siemplify.parameters["Group Ids Or Names"]
    is_id = siemplify.parameters.get("Is Id", "false").lower() == "true"

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
    ids = []
    output_message = ""
    errors = "\n\nErrors:\n\n"
    if group_ids_or_names:
        for _id in group_ids_or_names.split(","):
            _id = _id.strip()
            ids.append(_id)
    message = ""
    ret = {}
    if ids:
        for _id in ids:
            group = {}
            try:
                if is_id:
                    group = okta.get_group(_id)
                else:
                    groups = okta.list_groups(q=_id)
                    if isinstance(groups, list):
                        for g in groups:
                            if g["profile"]["name"] == _id:
                                group = g
                                break
                    else:
                        group = groups
                if group:
                    message += f'The group corresponding to "{_id}" was found.\n\n'
                    ret[_id] = group
                else:
                    message += f'No group corresponding to "{_id}" was found.\n\n'
            except Exception as err:
                siemplify.LOGGER.exception(err)
                siemplify.LOGGER.error(_id + ": " + str(err))
                errors += str(err) + "\n\n"
                pass
    if ret:
        for name, group in list(ret.items()):
            flat_group = dict_to_flat(group)
            csv_output = construct_csv([flat_group])
            siemplify.result.add_data_table(
                "Okta - Group: " + group["profile"]["name"], csv_output
            )
        output_message = message
    else:
        output_message = f"No groups were found. {message}"

    siemplify.end(output_message + errors, json.dumps(ret))


if __name__ == "__main__":
    main()
