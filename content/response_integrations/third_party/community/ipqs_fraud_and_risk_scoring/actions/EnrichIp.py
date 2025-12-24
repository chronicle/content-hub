from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler

from ..core.IPQSManager import PROVIDER, IPQSManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    data_json = {}
    api_key = siemplify.extract_configuration_param(PROVIDER, "API Key")
    strictness = int(
        siemplify.extract_action_param(param_name="Strictness", print_value=True),
    )
    user_agent = siemplify.extract_action_param(
        param_name="User Agent",
        print_value=True,
    )
    user_language = siemplify.extract_action_param(
        param_name="User Language",
        print_value=True,
    )
    fast = siemplify.extract_action_param(param_name="Fast", print_value=True)
    mobile = siemplify.extract_action_param(param_name="Mobile", print_value=True)
    allow_public_access_points = siemplify.extract_action_param(
        param_name="Allow Public Access Points",
        print_value=True,
    )
    lighter_penalties = siemplify.extract_action_param(
        param_name="Lighter Penalties",
        print_value=True,
    )
    data_json["strictness"] = strictness
    if user_agent != "":
        data_json["user_agent"] = user_agent
    if user_language != "":
        data_json["user_language"] = user_language
    if fast:
        data_json["fast"] = "true"
    if mobile:
        data_json["mobile"] = "true"
    if allow_public_access_points:
        data_json["allow_public_access_points"] = "true"
    if lighter_penalties:
        data_json["lighter_penalties"] = "true"

    ipqs_manager = IPQSManager(siemplify, api_key, data_json)
    ipqs_manager.enrich([EntityTypes.ADDRESS])


if __name__ == "__main__":
    main()
