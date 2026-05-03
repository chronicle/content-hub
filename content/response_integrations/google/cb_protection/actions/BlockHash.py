from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.CarbonBlackProtectionManager import CBProtectionManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    configurations = siemplify.get_configuration("CBProtection")
    server_addr = configurations["Api Root"]
    api_key = configurations["Api Key"]

    cb_protection = CBProtectionManager(server_addr, api_key)

    policies = siemplify.parameters.get("Policy Names", "").split(",")

    policy_ids = []

    for policy in policies:
        policy_ids.append(str(cb_protection.get_policy_by_name(policy).id))

    enriched_entities = []
    errors = ""

    for entity in siemplify.target_entities:
        try:
            if entity.entity_type == EntityTypes.FILEHASH:
                cb_protection.ban_hash(entity.identifier, policy_ids)
                enriched_entities.append(entity)
        except Exception as e:
            errors += f"Unable to block {entity.identifier}: \n{e}\n"
            continue

    if enriched_entities:
        entities_names = [entity.identifier for entity in enriched_entities]
        output_message = (
            "Carbon Black Protection - block the following hashes\n"
            + "\n".join(entities_names)
        )
        output_message += errors

        siemplify.update_entities(enriched_entities)

    else:
        output_message = "Carbon Black Protection - No suitable entities found.\n"
        output_message += errors

    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
