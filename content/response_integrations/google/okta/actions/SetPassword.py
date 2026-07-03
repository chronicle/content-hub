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
import string
import secrets
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..core.OktaManager import OktaManager
import json

PROVIDER = "Okta"
ACTION_NAME = "Okta - SetPassword"


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

    user_ids_or_logins = siemplify.parameters.get("User IDs Or Logins", "")
    new_password = siemplify.parameters["New Password"]
    is_add_random = (
        siemplify.parameters.get("Add 10 Random Chars", "false").lower() == "true"
    )
    is_scope = siemplify.parameters.get("Also Run On Scope", "false").lower() == "true"
    ids = []
    res = {}
    passwords = {}
    output_message = ""
    errors = "\n\nErrors:\n\n"
    if not is_add_random:
        if (
            len(new_password) < 8
            or new_password.lower() == new_password
            or new_password.upper() == new_password
        ):
            siemplify.end(
                "Password requirements were not met. Password requirements: at least 8 characters, a lowercase letter, an uppercase letter, a number, no parts of your username.",
                "false",
            )

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
    if user_ids_or_logins:
        for _id in user_ids_or_logins.split(","):
            _id = _id.strip()
            ids.append(_id)
    message = ""
    if ids:
        for _id in ids:
            if is_add_random:
                allchars = string.ascii_letters + string.punctuation + string.digits
                random_10 = "".join(secrets.choice(allchars) for _ in range(0, 10))
                new_password += random_10
            try:
                res = okta.set_password(_id, new_password=new_password)
                if res:
                    passwords.update({_id: new_password})
                    message += f"The password was set successfully for user with id {_id}: {new_password}\n\n"
                else:
                    message = (
                        f"The password couldn't be set for user with id {_id}.\n\n"
                    )
            except Exception as err:
                siemplify.LOGGER.exception(err)
                siemplify.LOGGER.error(_id + ": " + err)
                errors += err + "\n\n"
                pass
    if is_scope:
        for entity in siemplify.target_entities:
            if (
                entity.entity_type == EntityTypes.USER
                or entity.entity_type == EntityTypes.HOSTNAME
            ):
                if is_add_random:
                    allchars = string.ascii_letters + string.punctuation + string.digits
                    random_10 = "".join(secrets.choice(allchars) for _ in range(0, 10))
                    new_password += random_10
                try:
                    res = okta.set_password(
                        entity.identifier, new_password=new_password
                    )
                    if res:
                        passwords.update({entity.identifier: new_password})
                        message += f'The password was set successfully for user "{entity.identifier}": {new_password}\n\n'
                    else:
                        message += f'The password couldn\'t be set for user "{entity.identifier}".\n\n'
                except Exception as err:
                    siemplify.LOGGER.exception(err)
                    siemplify.LOGGER.error(entity.identifier + ": " + err)
                    errors += err + "\n\n"
                    pass
            else:
                continue
    if passwords:
        output_message = message
    else:
        output_message = f"No passwords were set. {message}"
    siemplify.end(output_message + errors, json.dumps(passwords))


if __name__ == "__main__":
    main()
