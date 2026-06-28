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
from okta.core.OktaManager import OktaManager

PROVIDER = "Okta"
ACTION_NAME = "Okta - UnassignRole"


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
    role_types = siemplify.parameters["Role IDs Or Names"]
    is_role_id = siemplify.parameters.get("Is Id", "false").lower() == "true"
    is_scope = siemplify.parameters.get("Also Run On Scope", "false").lower() == "true"
    roles = []
    ids = []
    res = {}
    ret = {}
    flag = False
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
                        if is_role_id:
                            res = okta.unassign_role(_id, role)
                        else:
                            role_id = okta.find_role_id_by_name(_id, role)
                            if role_id:
                                res = okta.unassign_role(_id, role_id)
                            else:
                                message += (
                                    _id + f": Couldn't find role id for {role}.\n\n"
                                )
                                continue
                        if res:
                            ret[_id].append(role)
                            flag = True
                            message += f"The user with id {_id} was unassigned the role {role}.\n\n"
                        else:
                            message += f"The user with id {_id} couldn't be unassigned the role {role}.\n\n"
                    except Exception as err:
                        siemplify.LOGGER.exception(err)
                        siemplify.LOGGER.error(_id + ", " + role + ": " + err)
                        errors += err + "\n\n"
                        pass
    if is_scope:
        entitiesUnassigned = []
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
                                if is_role_id:
                                    res = okta.unassign_role(_id, role)
                                else:
                                    role_id = okta.find_role_id_by_name(_id, role)
                                    if role_id:
                                        res = okta.unassign_role(_id, role_id)
                                    else:
                                        message += (
                                            entity.identifier
                                            + f": Couldn't find role id {role}.\n\n"
                                        )
                                        continue
                                if res:
                                    entitiesUnassigned.append(entity)
                                    ret[entity.identifier].append(role)
                                    flag = True
                                    message += f'The user "{entity.identifier}" was unassigned the role {role}.\n\n'
                                else:
                                    message += f'The user "{entity.identifier}" couldn\'t be unassigned the role {role}.\n\n'
                            except Exception as err:
                                siemplify.LOGGER.exception(err)
                                siemplify.LOGGER.error(
                                    entity.identifier + ", " + role + ": " + err
                                )
                                errors += err + "\n\n"
                                pass
                else:
                    message += f'Couldn\'t find the user "{entity.identifier}".\n\n'
                    continue
            else:
                continue
    success = "false"
    if ret and flag:
        output_message = message
        success = "true"
    else:
        output_message = f"No users were unassigned roles. {message}"
    siemplify.end(output_message + errors, success)


if __name__ == "__main__":
    main()
