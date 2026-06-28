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
ACTION_NAME = "Okta - AddGroup"


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

    name = siemplify.parameters["Group Name"]
    description = siemplify.parameters.get("Group Description", "")
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
    group = {}
    profile = {}
    profile["name"] = name
    profile["description"] = description
    errors = "\n\nErrors:\n\n"
    try:
        group = okta.add_group(profile)
    except Exception as err:
        siemplify.LOGGER.exception(err)
        siemplify.LOGGER.error(err)
        errors += str(err) + "\n\n"
        pass
    if group:
        output_message = f'A group with the name "{name}" was successfully created.'
        flat_group = dict_to_flat(group)
        csv_output = construct_csv([flat_group])
        siemplify.result.add_data_table("Okta - Group ", csv_output)
    else:
        output_message = "The group wasn't created."
        try:
            groups = okta.list_groups(q=profile["name"])
            if isinstance(groups, list):
                for g in groups:
                    if g["profile"]["name"] == profile["name"]:
                        flat_group = dict_to_flat(g)
                        csv_output = construct_csv([flat_group])
                        siemplify.result.add_data_table(
                            f"Okta - Group {name}", csv_output
                        )
                        siemplify.end(
                            "The group already exists.\n\n" + errors, json.dumps(g)
                        )
            else:
                flat_group = dict_to_flat(group)
                csv_output = construct_csv([flat_group])
                siemplify.result.add_data_table(f"Okta - Group {name}", csv_output)
                siemplify.end(
                    "The group already exists.\n\n" + errors, json.dumps(groups)
                )
        except Exception as err:
            siemplify.LOGGER.exception(err)
            siemplify.LOGGER.error(err)
            errors += str(err) + "\n\n"
            pass
    siemplify.end(output_message + errors, json.dumps(group))


if __name__ == "__main__":
    main()
