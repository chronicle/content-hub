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
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import construct_csv, dict_to_flat
from ..core.OktaManager import OktaManager
import json

PROVIDER = "Okta"
ACTION_NAME = "Okta - GetUser"


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

    user_ids_or_logins = siemplify.parameters.get("User Ids Or Logins")
    is_scope = siemplify.parameters.get("Also Run On Scope", "false").lower() == "true"
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

    errors = "\n\nErrors:\n\n"
    if user_ids_or_logins:
        for _id in user_ids_or_logins.split(","):
            _id = _id.strip()
            ids.append(_id)
    message = ""
    ret = {}
    if ids:
        for _id in ids:
            user = {}
            try:
                user = okta.get_user(_id)
                if user:
                    message += f'The user "{_id}" was found.\n\n'
                    ret[_id] = user
                else:
                    message += f'The user "{_id}" was not found.\n\n'
            except Exception as err:
                siemplify.LOGGER.exception(err)
                siemplify.LOGGER.error(_id + ": " + str(err))
                errors += str(err) + "\n\n"
                pass
    if is_scope:
        entitiesDisabled = []
        for entity in siemplify.target_entities:
            if (
                entity.entity_type == EntityTypes.USER
                or entity.entity_type == EntityTypes.HOSTNAME
            ):
                try:
                    user = okta.get_user(entity.identifier)
                    if user:
                        entitiesDisabled.append(entity)
                        message += f'The user "{entity.identifier}" was found.\n\n'
                        ret[entity.identifier] = user
                    else:
                        message += (
                            f'The user "{entity.identifier}" couldn\'t be found.\n\n'
                        )
                        continue
                except Exception as err:
                    siemplify.LOGGER.exception(err)
                    siemplify.LOGGER.error(entity.identifier + ": " + str(err))
                    errors += str(err) + "\n\n"
                    pass
            else:
                continue
    if ret:
        siemplify.result.add_result_json(list(ret.values()))
        for name, user in list(ret.items()):
            flat_user = dict_to_flat(user)
            csv_output = construct_csv([flat_user])
            siemplify.result.add_data_table("Okta - User: " + name, csv_output)
        output_message = message
    else:
        output_message = f"No users were found. {message}"

    siemplify.end(output_message + errors, json.dumps(ret))


if __name__ == "__main__":
    main()
