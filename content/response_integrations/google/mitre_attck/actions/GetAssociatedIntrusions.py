from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from ..core.MitreAttckManager import MitreAttckManager, USES_RELATIONSHIP
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv

INTEGRATION_NAME = "MitreAttck"
SCRIPT_NAME = "Mitre Att&ck - Get Associated Intrusions"
ID_IDENTIFIER = "Attack ID"
EXTERNAL_ID_IDENTIFIER = "External Attack ID"
NAME_IDENTIFIER = "Attack Name"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    result_value = False
    status = EXECUTION_STATE_FAILED
    intrusions = []
    attack_id = ""
    attack = None
    source_refs = []
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="API Root", input_type=str
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        print_value=True,
    )

    # INIT ACTION PARAMETERS:
    identifier = extract_action_param(
        siemplify, param_name="Technique ID", print_value=True, is_mandatory=True
    )
    identifier_type = extract_action_param(
        siemplify,
        param_name="Identifier Type",
        print_value=True,
        is_mandatory=True,
        default_value=ID_IDENTIFIER,
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Intrusions to Return",
        print_value=True,
        input_type=int,
        default_value=20,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = MitreAttckManager(api_root, verify_ssl)

        if identifier_type == ID_IDENTIFIER:
            attack_id = identifier
        else:
            if identifier_type == NAME_IDENTIFIER:
                attack = manager.get_attack_pattern_by_name(identifier)
            elif identifier_type == EXTERNAL_ID_IDENTIFIER:
                attack = manager.get_attack_pattern_by_external_id(identifier)
            if attack:
                attack_id = attack.attack_id

        if attack_id:
            for uses_relationship in manager.get_relationships_where_target_ref(
                attack_id, USES_RELATIONSHIP
            ):
                if hasattr(uses_relationship, "source_ref"):
                    source_refs.append(uses_relationship.source_ref)

        if source_refs:
            intrusions = manager.get_all_where_id_in(source_refs, limit)

        if intrusions:
            output_message = f"Found associated intrusions with {identifier} technique!"
            siemplify.result.add_data_table(
                title=f"Associated Intrusions for {identifier}",
                data_table=construct_csv(
                    [intrusion.to_intrusion_data_table() for intrusion in intrusions]
                ),
            )
            siemplify.result.add_result_json(
                [intrusion.to_json() for intrusion in intrusions]
            )
            for intrusion in intrusions:
                if intrusion.url and intrusion.mitre_external_id:
                    siemplify.result.add_link(
                        f"Link for the external reference: {intrusion.mitre_external_id}",
                        intrusion.url,
                    )
            result_value = True
        else:
            output_message = (
                f"Didn't find any intrusion associated with {identifier} technique!"
            )

        status = EXECUTION_STATE_COMPLETED
        siemplify.LOGGER.info("Finished processing")
    except Exception as e:
        siemplify.LOGGER.error(
            f"Error fetching associated intrusions for technique: {identifier}"
        )
        siemplify.LOGGER.exception(e)
        output_message = (
            f'Error executing action "Get Associated Intrusions". Reason:{e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
