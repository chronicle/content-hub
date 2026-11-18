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
ACTION_NAME = "Okta - AssignRole"


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

    user_ids = siemplify.parameters.get("User IDs", "")
    role_types = siemplify.parameters["Role Types"]
    is_scope = siemplify.parameters.get("Also Run On Scope", "false").lower() == "true"
    roles = []
    ids = []
    res = {}
    ret = {}
    output_message = ""
    errors = "\n\nErrors:\n\n"
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
    if user_ids:
        for _id in user_ids.split(","):
            _id = _id.strip()
            ids.append(_id)
    if role_types:
        for role in role_types.split(","):
            role = role.strip()
            roles.append(role)
    message = ""
    if ids:
        for _id in ids:
            if roles:
                ret[_id] = []
                for role in roles:
                    try:
                        res = okta.assign_role(_id, role)
                        if res:
                            ret[_id].append(res)
                            message += f"The user with id {_id} was assigned the role {role}.\n\n"
                        else:
                            message += f"The user with id {_id} couldn't be assigned the role {role}.\n\n"
                    except Exception as err:
                        siemplify.LOGGER.exception(err)
                        siemplify.LOGGER.error(_id + ", " + role + ": " + str(err))
                        errors += str(err) + "\n\n"
                        pass
    if is_scope:
        entitiesAssigned = []
        for entity in siemplify.target_entities:
            if (
                entity.entity_type == EntityTypes.USER
                or entity.entity_type == EntityTypes.HOSTNAME
            ):
                _id = okta.login_to_id(entity.identifier)
                if _id:
                    if roles:
                        ret[entity.identifier] = []
                        for role in roles:
                            try:
                                res = okta.assign_role(_id, role)
                                if res:
                                    entitiesAssigned.append(entity)
                                    ret[entity.identifier].append(res)
                                    message += f'The user "{entity.identifier}" was assigned the role {role}.\n\n'
                                else:
                                    message += f'The user "{entity.identifier}" couldn\'t be assigned the role {role}.\n\n'
                            except Exception as err:
                                siemplify.LOGGER.exception(err)
                                siemplify.LOGGER.error(
                                    entity.identifier + ", " + role + ": " + str(err)
                                )
                                errors += str(err) + "\n\n"
                                pass
                else:
                    message += f'Couldn\'t find the user "{entity.identifier}".\n\n'
                    continue
            else:
                continue
    if ret:
        flag = False
        output_message = message
        for user, roles in list(ret.items()):
            rows = []
            if roles:
                for role in roles:
                    if role:
                        flat_role = dict_to_flat(role)
                        rows.append(flat_role)
            if rows:
                flag = True
                csv_output = construct_csv(rows)
                siemplify.result.add_data_table(
                    f'Okta - User "{user}" Roles', csv_output
                )
        if not flag:
            output_message = f"No users were assigned roles. {message}"
    else:
        output_message = f"No users were assigned roles. {message}"
    siemplify.end(output_message + errors, json.dumps(ret))


if __name__ == "__main__":
    main()
