from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.IPVoidManager import IPVoidManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("IPVoid")
    api_root = conf["Api Root"]
    api_key = conf["Api Key"]
    use_ssl = conf.get("Use SSL", "False").lower() == "true"

    ipvoid_manager = IPVoidManager(api_root, api_key, use_ssl=use_ssl)

    found_entities = []

    for entity in siemplify.target_entities:
        if (
            entity.entity_type == EntityTypes.ADDRESS
            or entity.entity_type == EntityTypes.HOSTNAME
        ):
            html_report = ipvoid_manager.get_whois_html_report(entity.identifier)
            siemplify.result.add_entity_html_report(
                entity.identifier, "WhoIs Report", html_report
            )

            found_entities.append(entity)

    if found_entities:
        entities_names = [entity.identifier for entity in found_entities]

        output_message = (
            "IPVoid: Attached report for the following entities:\n"
            + "\n".join(entities_names)
        )

    else:
        output_message = "IPVoid: No reports were found."

    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
