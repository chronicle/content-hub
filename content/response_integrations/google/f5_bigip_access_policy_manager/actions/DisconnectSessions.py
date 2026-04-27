from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.F5BIGIPAccessPolicyManagerManager import F5BIGIPAccessPolicyManagerManager
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..core.constants import INTEGRATION_NAME, DISCONNECT_SESSIONS_ACTION


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = DISCONNECT_SESSIONS_ACTION
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="BIG-IP APM Address",
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
    )
    token_timeout = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Token Timeout (in Seconds)",
        is_mandatory=False,
        input_type=int,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        is_mandatory=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""
    session_ids_list = []  # CSV of session_ids split by comma to a list
    logon_user_names_list = []  # CSV of logon_user_names split by comma to a list
    client_ips_list = []  # CSV of client_ips split by comma to a list

    all_found_session_ids = []  # all objects session_ids found in F5
    successful_session_ids = []  # all successful session_ids
    failed_session_ids = []  # all failed session_ids

    found_client_ips = []  # client_ips found in F5
    found_logon_users = []  # user_logon_names found in F5
    found_session_ids = []  # session_ids found in F5

    not_found_client_ips = (
        []
    )  # list of all client_ips given by the user and not found in F5
    not_found_logon_user_names = (
        []
    )  # list of all user_logon_names given by the user and not found in F5
    not_found_session_ids = (
        []
    )  # list of all session_ids given by the user and not found in F5

    try:
        use_case_entities = extract_action_param(
            siemplify,
            param_name="Use Case Entities",
            is_mandatory=False,
            print_value=True,
            input_type=bool,
        )
        session_ids = extract_action_param(
            siemplify,
            param_name="Session IDs",
            is_mandatory=False,
            print_value=True,
            input_type=str,
        )
        logon_user_names = extract_action_param(
            siemplify,
            param_name="Logon User Names",
            is_mandatory=False,
            print_value=True,
            input_type=str,
        )
        client_ips = extract_action_param(
            siemplify,
            param_name="Client IPs",
            is_mandatory=False,
            print_value=True,
            input_type=str,
        )

        f5bigip_manager = F5BIGIPAccessPolicyManagerManager(
            api_root=api_root,
            username=username,
            password=password,
            token_timeout=token_timeout,
            verify_ssl=verify_ssl,
        )

        if use_case_entities:
            # Process use case entities and ignore the other user params
            for entity in siemplify.target_entities:
                if entity.entity_type == EntityTypes.ADDRESS:
                    client_ips_list.append(entity.identifier)
                if entity.entity_type == EntityTypes.USER:
                    logon_user_names_list.append(entity.identifier)
        else:
            # Process the other user params and ignore use case entities
            if client_ips:
                client_ips_list = [
                    client_ip.strip() for client_ip in client_ips.split(",")
                ]
            if logon_user_names:
                logon_user_names_list = [
                    logon_user_name.strip()
                    for logon_user_name in logon_user_names.split(",")
                ]
            if session_ids:
                session_ids_list = [
                    session_id.strip() for session_id in session_ids.split(",")
                ]

        object_to_disconnect = (
            client_ips_list + logon_user_names_list + session_ids_list
        )

        # Fetch all active sessions from F5
        list_of_sessions = f5bigip_manager.list_active_sessions(limit=0)

        for active_session in list_of_sessions:
            if active_session.client_ip in client_ips_list:
                all_found_session_ids.append(active_session.active_session_id)
                found_client_ips.append(active_session.client_ip)

            if active_session.logon_user in logon_user_names_list:
                all_found_session_ids.append(active_session.active_session_id)
                found_logon_users.append(active_session.logon_user)

            if active_session.active_session_id in session_ids_list:
                all_found_session_ids.append(active_session.active_session_id)
                found_session_ids.append(active_session.active_session_id)

        all_found_session_ids = list(set(all_found_session_ids))

        for session_id in all_found_session_ids:
            try:
                f5bigip_manager.disconnect_session(session_id=session_id)
                successful_session_ids.append(session_id)
            except Exception:
                failed_session_ids.append(session_id)

        # F5 disconnect request returns success event when disconnect action fails, because of this we should get
        # remaining list of sessions and check if sessions were successfully disconnected
        remaining_list_of_sessions = f5bigip_manager.list_active_sessions(limit=0)
        remaining_list_of_session_ids = [
            session.active_session_id for session in remaining_list_of_sessions
        ]

        for session_id in successful_session_ids:
            if session_id in remaining_list_of_session_ids:
                failed_session_ids.append(session_id)

        successful_session_ids = list(
            set(successful_session_ids) - set(failed_session_ids)
        )

        # Get all objects that were not found in F5
        objects_not_found = list(
            set(object_to_disconnect)
            - set(found_client_ips)
            - set(found_logon_users)
            - set(found_session_ids)
        )

        # Split not found objects into different object types
        for object_not_found in objects_not_found:
            if object_not_found in client_ips_list:
                not_found_client_ips.append(object_not_found)
            elif object_not_found in logon_user_names_list:
                not_found_logon_user_names.append(object_not_found)
            elif object_not_found in session_ids_list:
                not_found_session_ids.append(object_not_found)

        if not all_found_session_ids:
            status = EXECUTION_STATE_FAILED
            result_value = False

            if not use_case_entities:
                # If no session_ids found based on user's inputs
                output_message += (
                    "Could not find any of the provided inputs in the Active Sessions List, please "
                    "check the inputs you have provided and try again."
                )
            else:
                # If no session_ids found based siemplify case entities
                output_message += (
                    "Could not find any of the provided entities in the Active Sessions List, please "
                    "check the inputs you have provided and try again."
                )

        else:
            output_message += f"\nSuccessfully disconnected sessions for the following Session IDs: {', '.join([session_id for session_id in successful_session_ids])}."

            if failed_session_ids:
                output_message += f"\nFailed to disconnect sessions with the following Session IDs: {', '.join([session_id for session_id in failed_session_ids])}."

            if not_found_client_ips:
                output_message += f"\nCouldn't find the following Clients IPs in any of the active sessions: {', '.join([client_ip for client_ip in not_found_client_ips])}."
            if not_found_logon_user_names:
                output_message += f"\nCouldn't find the following Logon User Names in any of the active sessions: {', '.join([logon_name for logon_name in not_found_logon_user_names])}."
            if not_found_session_ids:
                output_message += f"\nCouldn't find the following Session IDs in any of the active sessions: {', '.join([session_id for session_id in not_found_session_ids])}."

    except Exception as e:
        output_message += (
            f"Failed to perform action {DISCONNECT_SESSIONS_ACTION}! Error is {e}"
        )
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
