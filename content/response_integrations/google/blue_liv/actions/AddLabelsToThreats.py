from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.BlueLivManager import BlueLivManager
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.consts import INTEGRATION_NAME, ADD_LABELS_TO_THREATS


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_LABELS_TO_THREATS
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="User Name",
        is_mandatory=True,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
        print_value=False,
    )
    organization_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Organization ID",
        is_mandatory=True,
        print_value=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        is_mandatory=True,
    )

    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""
    existing_labels = []
    existing_labels_names = []
    nonexisting_labels = []
    existing_threats = []
    nonexisting_threats = []
    threats_labels = {}
    labels_mapping = {}
    added_labels_to_threats = {}

    try:
        siemplify.LOGGER.info("----------------- Main - Started -----------------")
        module_id = extract_action_param(
            siemplify,
            param_name="Module ID",
            is_mandatory=True,
            print_value=True,
            input_type=str,
        )
        module_type = extract_action_param(
            siemplify,
            param_name="Module Type",
            is_mandatory=True,
            print_value=True,
            input_type=str,
        )
        module_type = module_type.lower()
        threat_ids = extract_action_param(
            siemplify,
            param_name="Resource ID",
            is_mandatory=True,
            print_value=True,
            input_type=str,
        )
        threat_ids = [threat.strip() for threat in threat_ids.split(",")]
        label_names = extract_action_param(
            siemplify,
            param_name="Label Names",
            is_mandatory=True,
            print_value=True,
            input_type=str,
        )
        label_names = [label.strip() for label in label_names.split(",")]

        blueliv_manager = BlueLivManager(
            api_root=api_root,
            username=username,
            password=password,
            organization_id=organization_id,
            verify_ssl=verify_ssl,
        )

        labels = blueliv_manager.get_labels()

        for given_label in label_names:  # need to check given labels
            for api_label in labels:
                if (
                    given_label == api_label.label_name
                    and str(api_label.label_module_id) == module_id
                ):
                    label_id = api_label.label_id
                    labels_mapping[label_id] = given_label
                    existing_labels.append(
                        label_id
                    )  # List of label IDs for next request
                    existing_labels_names.append(
                        given_label
                    )  # List of label names for output

        nonexisting_labels = list(set(label_names) - set(existing_labels_names))

        if len(nonexisting_labels) == len(label_names):
            raise Exception("None of the labels were found. Please check the spelling.")

        else:
            if nonexisting_labels:
                output_message += f"\n Couldn't find the following labels in BlueLiv: {', '.join([label for label in nonexisting_labels])}. Please check the label names you have provided in the action parameters and try again."

            for (
                threat_id
            ) in threat_ids:  # need to check each given threat if it exist in BlueLiv
                try:
                    blueliv_manager.check_if_threat_exist(
                        module_id=module_id,
                        module_type=module_type,
                        threat_id=threat_id,
                    )
                    existing_threats.append(threat_id)

                    current_labels = blueliv_manager.get_threat_with_details(
                        module_id=module_id,
                        module_type=module_type,
                        threat_id=threat_id,
                    )
                    current_labels = [
                        label.get("id") for label in current_labels.labels
                    ]
                    threats_labels[threat_id] = current_labels

                except Exception as e:
                    nonexisting_threats.append(threat_id)

            if len(nonexisting_threats) == len(threat_ids):
                raise Exception(
                    "None of the threats were found. Please check the spelling."
                )

            else:
                if nonexisting_threats:
                    output_message += f"\n Couldn't find the following threats in BlueLiv {', '.join([threat for threat in nonexisting_threats])}. Please check the threat IDs you have provided in the action parameters and try again."

                for threat in existing_threats:
                    if not added_labels_to_threats.get(threat):
                        added_labels_to_threats[threat] = {"success": [], "failed": []}

                    for label in existing_labels:
                        if label not in threats_labels.get(threat):
                            blueliv_manager.add_label_to_threat(
                                label=label,
                                module_id=module_id,
                                module_type=module_type,
                                threat_id=threat,
                            )
                            threat_labels_sucess = added_labels_to_threats[threat].get(
                                "success"
                            )
                            threat_labels_sucess.append(label)
                            added_labels_to_threats[threat][
                                "success"
                            ] = threat_labels_sucess
                        else:
                            threat_labels_failed = added_labels_to_threats[threat].get(
                                "failed"
                            )
                            threat_labels_failed.append(label)
                            added_labels_to_threats[threat][
                                "failed"
                            ] = threat_labels_failed

                for threat_id, added_labels in added_labels_to_threats.items():

                    labels_success = [
                        labels_mapping.get(label)
                        for label in added_labels.get("success")
                    ]
                    labels_failed = [
                        labels_mapping.get(label)
                        for label in added_labels.get("failed")
                    ]
                    if labels_success:
                        output_message += f"\n Successfully added the following labels to the following threat {threat_id} in Blueliv: {', '.join([label for label in labels_success])}."

                    if labels_failed:
                        output_message += f"\n The following labels were already a part of the threat {threat_id} in Blueliv: {', '.join([label for label in labels_failed])}."

    except Exception as e:
        output_message = f"Error executing action {ADD_LABELS_TO_THREATS}. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
