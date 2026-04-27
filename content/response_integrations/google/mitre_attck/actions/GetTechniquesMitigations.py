from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from ..core.MitreAttckManager import MitreAttckManager, MITIGATES_RELATIONSHIP
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv


INTEGRATION_NAME = "MitreAttck"
SCRIPT_NAME = "Mitre Att&ck - Get Techniques Mitigations"
ID_IDENTIFIER = "Attack ID"
EXTERNAL_ID_IDENTIFIER = "External Attack ID"
NAME_IDENTIFIER = "Attack Name"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
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
    identifiers = extract_action_param(
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
        param_name="Max Mitigations to Return",
        print_value=True,
        input_type=int,
        default_value=20,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    json_result = {}
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    succeeded_identifiers = []
    failed_identifiers = []
    output_message = ""

    try:
        # Split techniques IDs
        identifiers = (
            [identifier.strip() for identifier in identifiers.split(",")]
            if identifiers
            else []
        )
        manager = MitreAttckManager(api_root, verify_ssl)

        if not manager.test_connectivity():
            output_message = "Unable to connect to MitreAttack"
            status = EXECUTION_STATE_FAILED
            result_value = "false"
        else:
            for identifier in identifiers:
                try:
                    intrusions = []
                    attack_id = ""
                    attack = None
                    source_refs = []

                    siemplify.LOGGER.info(f"Processing technique {identifier}.")

                    if identifier_type == ID_IDENTIFIER:
                        attack_id = identifier
                    else:
                        if identifier_type == NAME_IDENTIFIER:
                            siemplify.LOGGER.info("Fetching attack pattern.")
                            attack = manager.get_attack_pattern_by_name(identifier)
                        elif identifier_type == EXTERNAL_ID_IDENTIFIER:
                            siemplify.LOGGER.info("Fetching attack pattern.")
                            attack = manager.get_attack_pattern_by_external_id(
                                identifier
                            )

                        if attack:
                            attack_id = attack.attack_id

                    if attack_id:
                        for relationship in manager.get_relationships_where_target_ref(
                            attack_id, MITIGATES_RELATIONSHIP
                        ):
                            if hasattr(relationship, "source_ref"):
                                source_refs.append(relationship.source_ref)

                    if source_refs:
                        intrusions = manager.get_all_where_id_in(source_refs, limit)

                    if intrusions:
                        siemplify.LOGGER.info(
                            f"Found {len(intrusions)} mitigations for technique {identifier}."
                        )
                        json_result[identifier] = {
                            "mitigations": [
                                intrusion.to_json() for intrusion in intrusions
                            ]
                        }

                        siemplify.result.add_data_table(
                            title=f"Mitigation techniques for {identifier}",
                            data_table=construct_csv(
                                [
                                    intrusion.to_mitigations_data_table()
                                    for intrusion in intrusions
                                ]
                            ),
                        )

                        for intrusion in intrusions:
                            if intrusion.url and intrusion.mitre_external_id:
                                siemplify.result.add_link(
                                    f"Link for the external reference: {intrusion.mitre_external_id}",
                                    intrusion.url,
                                )
                        succeeded_identifiers.append(identifier)

                    else:
                        siemplify.LOGGER.info(
                            f"No mitigations were found for technique {identifier}."
                        )
                        failed_identifiers.append(identifier)

                except Exception as e:
                    siemplify.LOGGER.error(
                        f"An error occurred on Technique {identifier}"
                    )
                    siemplify.LOGGER.exception(e)
                    failed_identifiers.append(identifier)

            if succeeded_identifiers:
                output_message += "Successfully retrieved mitigations for the following techniques:\n   {}".format(
                    "\n   ".join(succeeded_identifiers)
                )

            else:
                output_message += "No mitigations were found."
                result_value = False

            if failed_identifiers:
                output_message += "\n\nAction wasn't able to find mitigations for the following techniques:\n   {}".format(
                    "\n   ".join(failed_identifiers)
                )

    except Exception as e:
        siemplify.LOGGER.error("Error fetching Techniques Mitigations")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = (
            f'Error executing action "Get Techniques Mitigations". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_result))
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
