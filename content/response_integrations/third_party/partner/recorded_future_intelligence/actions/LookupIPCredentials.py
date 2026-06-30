############################## TERMS OF USE ################################### # noqa: E266
# The following code is provided for demonstration purposes only, and should  #
# not be used without independent verification. Recorded Future makes no      #
# representations or warranties, express, implied, statutory, or otherwise,   #
# regarding this code, and provides it strictly "as-is".                      #
# Recorded Future shall not be liable for, and you assume all risk of         #
# using the foregoing.                                                        #
###############################################################################

from __future__ import annotations

from psengine.config import Config
from psengine.identity import IdentityMgr
from psengine.identity.errors import IdentityLookupError
from pydantic import ValidationError
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.constants import PROVIDER_NAME
from ..core.version import __version__ as version


@output_handler
def main():
    siemplify = SiemplifyAction()

    api_key = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="ApiKey",
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    ip = extract_action_param(
        siemplify,
        param_name="IP",
        input_type=str,
        is_mandatory=False,
        print_value=True,
        remove_whitespaces=True,
    )
    is_target_entities = extract_action_param(
        siemplify,
        param_name="Filter on Target Entities",
        input_type=bool,
        print_value=True,
        default_value=False,
        is_mandatory=False,
    )
    range_gte = extract_action_param(
        siemplify,
        param_name="Range GTE",
        input_type=str,
        is_mandatory=False,
        print_value=True,
        remove_whitespaces=True,
    )
    range_gt = extract_action_param(
        siemplify,
        param_name="Range GT",
        input_type=str,
        is_mandatory=False,
        print_value=True,
        remove_whitespaces=True,
    )
    range_lte = extract_action_param(
        siemplify,
        param_name="Range LTE",
        input_type=str,
        is_mandatory=False,
        print_value=True,
        remove_whitespaces=True,
    )
    range_lt = extract_action_param(
        siemplify,
        param_name="Range LT",
        input_type=str,
        is_mandatory=False,
        print_value=True,
        remove_whitespaces=True,
    )
    first_downloaded_gte = extract_action_param(
        siemplify,
        param_name="First Downloaded GTE",
        input_type=str,
        is_mandatory=False,
        print_value=True,
        remove_whitespaces=True,
    )
    latest_downloaded_gte = extract_action_param(
        siemplify,
        param_name="Latest Downloaded GTE",
        input_type=str,
        is_mandatory=False,
        print_value=True,
        remove_whitespaces=True,
    )
    exfiltration_date_gte = extract_action_param(
        siemplify,
        param_name="Exfiltration Date GTE",
        input_type=str,
        is_mandatory=False,
        print_value=True,
        remove_whitespaces=True,
    )
    properties = extract_action_param(
        siemplify,
        param_name="Properties",
        input_type=str,
        is_mandatory=False,
        print_value=True,
        remove_whitespaces=True,
    )
    breach_name = extract_action_param(
        siemplify,
        param_name="Breach Name",
        input_type=str,
        is_mandatory=False,
        print_value=True,
        remove_whitespaces=True,
    )
    breach_date = extract_action_param(
        siemplify,
        param_name="Breach Date",
        input_type=str,
        is_mandatory=False,
        print_value=True,
        remove_whitespaces=True,
    )
    dump_name = extract_action_param(
        siemplify,
        param_name="Dump Name",
        input_type=str,
        is_mandatory=False,
        print_value=True,
        remove_whitespaces=True,
    )
    dump_date = extract_action_param(
        siemplify,
        param_name="Dump Date",
        input_type=str,
        is_mandatory=False,
        print_value=True,
        remove_whitespaces=True,
    )
    username_properties = extract_action_param(
        siemplify,
        param_name="Username Properties",
        input_type=str,
        is_mandatory=False,
        print_value=True,
        remove_whitespaces=True,
    )
    authorization_technologies = extract_action_param(
        siemplify,
        param_name="Authorization Technologies",
        input_type=str,
        is_mandatory=False,
        print_value=True,
        remove_whitespaces=True,
    )
    authorization_protocols = extract_action_param(
        siemplify,
        param_name="Authorization Protocols",
        input_type=str,
        is_mandatory=False,
        print_value=True,
        remove_whitespaces=True,
    )
    malware_families = extract_action_param(
        siemplify,
        param_name="Malware Families",
        input_type=str,
        is_mandatory=False,
        print_value=True,
        remove_whitespaces=True,
    )
    organization_id = extract_action_param(
        siemplify,
        param_name="Organization ID",
        input_type=str,
        is_mandatory=False,
        print_value=True,
        remove_whitespaces=True,
    )
    max_results = extract_action_param(
        siemplify,
        param_name="Max Results",
        input_type=int,
        is_mandatory=False,
        print_value=True,
        default_value=500,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    is_success = True
    output_message = ""
    status = EXECUTION_STATE_COMPLETED

    try:
        ip = siemplify.target_entities if is_target_entities else ip
        if isinstance(ip, list):
            siemplify.LOGGER.info("Target IP contains multiple values, using the first")
            ip = ip[0].identifier
        
        siemplify.LOGGER.info("Initializing psengine configuration")
        Config.init(
            client_verify_ssl=verify_ssl,
            rf_token=api_key,
            app_id=f"ps-google-soar/{version}",
        )
        siemplify.LOGGER.info("Initializing psengine IdentityMgr")
        identity_mgr = IdentityMgr()
        siemplify.LOGGER.info("Searching credentials for given IP")
        lookup_resp = identity_mgr.lookup_ip(
            ip=ip,
            range_gte=range_gte,
            range_gt=range_gt,
            range_lte=range_lte,
            range_lt=range_lt,
            first_downloaded_gte=first_downloaded_gte,
            latest_downloaded_gte=latest_downloaded_gte,
            exfiltration_date_gte=exfiltration_date_gte,
            properties=properties,
            breach_name=breach_name,
            breach_date=breach_date,
            dump_name=dump_name,
            dump_date=dump_date,
            username_properties=username_properties,
            authorization_technologies=authorization_technologies,
            authorization_protocols=authorization_protocols,
            malware_families=malware_families,
            organization_id=organization_id,
            max_results=max_results,
        )
        data = [cred_result.json() for cred_result in lookup_resp]
        siemplify.result.add_result_json(data)
        output_message += (
            "Successfully searched credentials for the given IP"
        )

    except IndexError as err:
        output_message = f"Error parsing action target entities: {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except ValidationError as err:
        output_message = f"Error with Identity Manager parameters: {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except ValueError as err:
        output_message = f"Error creating Identity Manager: {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except IdentityLookupError as err:
        output_message = f"Error searching IP credentials: {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED

    except Exception as err:
        output_message = f"Error executing Lookup IP Credentials action: {err}"
        is_success = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {is_success}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, is_success, status)


if __name__ == "__main__":
    main()
