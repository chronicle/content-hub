from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.MicrosoftGraphSecurityManager import MicrosoftGraphSecurityManager


@output_handler
def main():
    siemplify = SiemplifyAction()

    client_id = siemplify.extract_configuration_param("Integration", "Client ID")
    secret_id = siemplify.extract_configuration_param("Integration", "Secret ID")
    tenant_id = siemplify.extract_configuration_param("Integration", "Tenant ID")
    create_insight = siemplify.extract_action_param("Create Insight", input_type=bool)
    certificate_password = siemplify.extract_configuration_param(
        "Integration",
        "Certificate Password",
    )
    certificate_path = siemplify.extract_configuration_param(
        "Integration",
        "Certificate Path",
    )
    user_email = siemplify.extract_action_param("User Email", print_value=True)

    siemplify.LOGGER.info("Connecting to Microsoft Graph Security.")
    mtm = MicrosoftGraphSecurityManager(
        client_id,
        secret_id,
        certificate_path,
        certificate_password,
        tenant_id,
    )
    siemplify.LOGGER.info("Connected successfully.")

    mfa_stats = []

    mfa_stats.append(mtm.get_user_mfa_stats(user_email))

    # Create given parameter user insight
    if create_insight:
        create_case_insight(siemplify, mfa_stats[0])

    for entity in siemplify.target_entities:
        if "@" in entity.identifier:
            print(entity.identifier)
            mfa_record = mtm.get_user_mfa_stats(entity.identifier)
            if mfa_record:
                mfa_stats.append(mfa_record)
                # Create remaining insights
                if create_insight:
                    create_case_insight(siemplify, mfa_record)

    status = EXECUTION_STATE_COMPLETED
    output_message = "success"
    result_value = "success"
    siemplify.result.add_result_json(mfa_stats)
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


def create_case_insight(siemplify, mfa_record):
    severity = 0
    entity_identifier = mfa_record["userPrincipalName"]
    insight_type = 1
    triggered_by = "Microsoft 365 MFA"
    title = "" + mfa_record["userPrincipalName"]
    content = f""" 
        <b>userPrincipalName:</b> {mfa_record["userPrincipalName"]}
        <b>userDisplayName:</b> {mfa_record["userDisplayName"]}
        <b>isRegistered:</b> {mfa_record["isRegistered"]}
        <b>isEnabled:</b> {mfa_record["isEnabled"]}
        <b>isCapable:</b> {mfa_record["isCapable"]}
        <b>isMfaRegistered:</b> {mfa_record["isMfaRegistered"]}
        <b>authMethods:</b> {mfa_record["authMethods"]}
    """

    siemplify.create_case_insight(
        triggered_by,
        title,
        content,
        entity_identifier,
        severity,
        insight_type,
    )


if __name__ == "__main__":
    main()
