from __future__ import annotations
import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.extraction import extract_configuration_param, extract_action_param

from ..core.BMCRemedyITSMManager import BMCRemedyITSMManager
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    CREATE_INCIDENT_SCRIPT_NAME,
)
from ..core.UtilsManager import get_names_from_customer


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_INCIDENT_SCRIPT_NAME
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
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    # action parameters
    incident_status = extract_action_param(
        siemplify, param_name="Status", print_value=True
    )
    impact = extract_action_param(siemplify, param_name="Impact", print_value=True)
    urgency = extract_action_param(siemplify, param_name="Urgency", print_value=True)
    description = extract_action_param(
        siemplify, param_name="Description", print_value=True
    )
    company = extract_action_param(siemplify, param_name="Company", print_value=True)
    customer = extract_action_param(siemplify, param_name="Customer", print_value=True)
    template_name = extract_action_param(
        siemplify, param_name="Template Name", print_value=True
    )
    incident_type = extract_action_param(
        siemplify, param_name="Incident Type", print_value=True
    )
    assigned_group = extract_action_param(
        siemplify, param_name="Assigned Group", print_value=True
    )
    assignee = extract_action_param(siemplify, param_name="Assignee", print_value=True)
    resolution = extract_action_param(
        siemplify, param_name="Resolution", print_value=True
    )
    resolution_category_tier_1 = extract_action_param(
        siemplify, param_name="Resolution Category Tier 1", print_value=True
    )
    resolution_category_tier_2 = extract_action_param(
        siemplify, param_name="Resolution Category Tier 2", print_value=True
    )
    resolution_category_tier_3 = extract_action_param(
        siemplify, param_name="Resolution Category Tier 3", print_value=True
    )
    resolution_product_category_tier_1 = extract_action_param(
        siemplify, param_name="Resolution Product Category Tier 1", print_value=True
    )
    resolution_product_category_tier_2 = extract_action_param(
        siemplify, param_name="Resolution Product Category Tier 2", print_value=True
    )
    resolution_product_category_tier_3 = extract_action_param(
        siemplify, param_name="Resolution Product Category Tier 3", print_value=True
    )
    reported_source = extract_action_param(
        siemplify, param_name="Reported Source", print_value=True
    )
    custom_fields = extract_action_param(
        siemplify, param_name="Custom Fields", print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result = False
    status = EXECUTION_STATE_COMPLETED
    manager = None
    output_message = ""

    try:
        try:
            custom_fields_dict = json.loads(custom_fields) if custom_fields else {}
        except Exception:
            raise Exception(
                'Invalid JSON payload provided in the parameter "Custom Fields". Please check the '
                "structure."
            )

        manager = BMCRemedyITSMManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        templates = []

        if template_name:
            templates = manager.get_templates_by_name(template_name)

            if not templates:
                raise Exception(
                    f'template with name "{template_name}" was not found. Please check the spelling '
                    f"or provide template ID directly via custom fields."
                )

        template_id = templates[0].template_id if templates else None
        last_name, first_name = (
            get_names_from_customer(customer) if customer else (None, None)
        )

        incident = manager.create_incident(
            status=incident_status,
            impact=impact,
            urgency=urgency,
            description=description,
            company=company,
            first_name=first_name,
            last_name=last_name,
            template_id=template_id,
            incident_type=incident_type,
            assigned_group=assigned_group,
            assignee=assignee,
            resolution=resolution,
            resolution_category_tier_1=resolution_category_tier_1,
            resolution_category_tier_2=resolution_category_tier_2,
            resolution_category_tier_3=resolution_category_tier_3,
            resolution_product_category_tier_1=resolution_product_category_tier_1,
            resolution_product_category_tier_2=resolution_product_category_tier_2,
            resolution_product_category_tier_3=resolution_product_category_tier_3,
            reported_source=reported_source,
            custom_fields=custom_fields_dict,
        )
        siemplify.result.add_result_json(incident.to_json())
        result = True
        status = EXECUTION_STATE_COMPLETED
        output_message = f"Successfully created incident in {INTEGRATION_DISPLAY_NAME}."

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {CREATE_INCIDENT_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action {CREATE_INCIDENT_SCRIPT_NAME}. Reason: {e}"
        )

    finally:
        try:
            if manager:
                siemplify.LOGGER.info(f"Logging out from {INTEGRATION_DISPLAY_NAME}..")
                manager.logout()
                siemplify.LOGGER.info(
                    f"Successfully logged out from {INTEGRATION_DISPLAY_NAME}"
                )
        except Exception as error:
            siemplify.LOGGER.error(f"Logging out failed. Error: {error}")
            siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
