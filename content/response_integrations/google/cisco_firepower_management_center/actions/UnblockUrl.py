from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.CiscoFirepowerManager import CiscoFirepowerManager
from soar_sdk.SiemplifyDataModel import EntityTypes

INTEGRATION_PROVIDER = "CiscoFirepowerManagementCenter"


@output_handler
def main():

    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration(INTEGRATION_PROVIDER)
    verify_ssl = str(conf.get("Verify SSL", "false").lower()) == str(True).lower()
    cisco_firepower_manager = CiscoFirepowerManager(
        conf["API Root"], conf["Username"], conf["Password"], verify_ssl
    )
    # Parameters.
    url_group_name = siemplify.parameters.get("URL Group Name")

    # variables.
    error_flag = False
    blocked_entities = []
    errors = []
    result_value = False

    # Set script name.
    siemplify.script_name = "CiscoFirepower_Unblock_URL"

    target_urls = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.URL
    ]

    # Get url group object to pass to the block function.
    url_group_object = cisco_firepower_manager.get_url_group_by_name(url_group_name)

    for url_entity in target_urls:
        try:
            cisco_firepower_manager.unblock_url(url_group_object, url_entity.identifier)
            result_value = True
            blocked_entities.append(url_entity.identifier)
        except Exception as err:
            error_message = (
                f'Error unblocking url "{url_entity.identifier}", ERROR: {err}.'
            )
            siemplify.LOGGER.error(error_message)
            siemplify.LOGGER.exception(err)
            error_flag = True
            errors.append(error_message)

    if result_value:
        output_message = (
            f'The following entities were unblocked: {",".join(blocked_entities)}'
        )
    else:
        output_message = "No entities were unblocked."

    if error_flag:
        output_message = "{0}  \n \n  ERRORS: {1}".format(
            output_message, " \n ".join(errors)
        )

    siemplify.end(output_message, True)


if __name__ == "__main__":
    main()
