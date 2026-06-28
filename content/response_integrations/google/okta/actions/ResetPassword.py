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
import json

PROVIDER = "Okta"
ACTION_NAME = "Okta - ResetPassword"


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
    send_email = siemplify.parameters.get("Send Email", "false").lower() == "true"
    is_scope = siemplify.parameters.get("Also Run On Scope", "false").lower() == "true"
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
    if user_ids_or_logins:
        for _id in user_ids_or_logins.split(","):
            _id = _id.strip()
            ids.append(_id)
    message = ""
    if ids:
        for _id in ids:
            try:
                res = okta.reset_password(_id, send_email_with_reset_link=send_email)
                if res:
                    if send_email:
                        message += f"The password reset was requested via email for user with id {_id}.\n\n"
                    else:
                        message += f"The password reset for user with id {_id} was requested. Link: {res['resetPasswordUrl']}.\n\n"
                    ret[_id] = res
                else:
                    if not send_email:
                        message += f"{_id}: Something went wrong."
                    else:
                        ret[_id] = res
                    continue
            except Exception as err:
                siemplify.LOGGER.exception(err)
                siemplify.LOGGER.error(f"{_id}: {err}")
                errors += f"{str(err)}\n\n"
                pass
    if is_scope:
        entitiesProcessed = []
        entityLinks = {}
        for entity in siemplify.target_entities:
            if (
                entity.entity_type == EntityTypes.USER
                or entity.entity_type == EntityTypes.HOSTNAME
            ):
                try:
                    res = okta.reset_password(
                        entity.identifier, send_email_with_reset_link=send_email
                    )
                    if res:
                        if not send_email:
                            entityLinks.update({entity.identifier: res})
                            message += (
                                f'The user "{entity.identifier}" must go to '
                                f"{res['resetPasswordUrl']} in order "
                                "to change his password.\n\n"
                            )
                        else:
                            message += f'The user "{entity.identifier}" was sent an email in order to change his password.\n\n'
                        entityLinks[entity.identifier] = res
                        entitiesProcessed.append(entity)
                        ret[entity.identifier] = res
                    else:
                        if not send_email:
                            message += f"{entity.identifier}: Something went wrong.\n\n"
                        else:
                            entityLinks[entity.identifier] = res
                        continue
                except Exception as err:
                    siemplify.LOGGER.exception(err)
                    siemplify.LOGGER.error(f"{entity.identifier}: {err}")
                    errors += f"{str(err)}\n\n"
                    pass
            else:
                continue
        # ret = entityLinks
    if ret:
        output_message = message
    else:
        output_message = f"No password reset requests could be processed. {message}"
    siemplify.end(output_message + errors, json.dumps(ret))


if __name__ == "__main__":
    main()
