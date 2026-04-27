from __future__ import annotations
from collections import defaultdict

from TIPCommon import extract_configuration_param, extract_action_param
from ..core import consts
from ..core.AWSWAFManager import AWSWAFManager
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import INTEGRATION_NAME, INTEGRATION_DISPLAY_NAME, DEFAULT_DDL_SCOPE
from ..core.exceptions import AWSWAFNotFoundException
from ..core.utils import (
    load_csv_to_set,
    mask_ip_address,
    get_ip_address_version,
    is_action_approaching_timeout,
    get_param_scopes,
)

SCRIPT_NAME = "Remove IP From IP Set"
SUPPORTED_ENTITIES = (EntityTypes.ADDRESS,)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # Integration configuration
    aws_access_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="AWS Access Key ID",
        is_mandatory=True,
    )

    aws_secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="AWS Secret Key",
        is_mandatory=True,
    )

    aws_default_region = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="AWS Default Region",
        is_mandatory=True,
    )

    # Action configuration
    ip_set_names = extract_action_param(
        siemplify, param_name="IP Set Names", is_mandatory=True, print_value=True
    )
    scope = extract_action_param(
        siemplify,
        param_name="Scope",
        is_mandatory=True,
        print_value=True,
        default_value=DEFAULT_DDL_SCOPE,
    )

    param_scope = scope  # input param scope
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = False
    output_message = ""

    supported_entities = []  # list of supported entities of type IP ADDRESS

    # ips that were successfully added to IP set. Key is IP Set "scoped name" (name concatenated to scope) . Value is list of IPs
    successful_ips_in_ipset = defaultdict(list)
    # ips that failed to add to IP set. Key is IP Set "scoped name" (name concatenated to scope) . Value is list of IPs
    failed_ips_in_ipset = defaultdict(list)
    # ips that were not found in IP set. Key is IP Set "scoped name" (name concatenated to scope) . Value is list of IPs
    non_existed_ips = defaultdict(list)

    status = EXECUTION_STATE_COMPLETED

    existing_ip_sets = (
        []
    )  # list of IP set that exist in WAF. Each item is an IPSet data model

    missed_ip_names = (
        {  # list of IP set name that were not found in a particular scope in WAF
            "REGIONAL": [],
            "CLOUDFRONT": [],
        }
    )

    try:
        ip_set_names = load_csv_to_set(csv=ip_set_names, param_name="IP Set Names")
        scopes = get_param_scopes(param_scope)

        siemplify.LOGGER.info(f"Connecting to {INTEGRATION_DISPLAY_NAME} Service")
        waf_client = AWSWAFManager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_default_region,
        )
        waf_client.test_connectivity()  # this validates the credentials
        siemplify.LOGGER.info(
            f"Successfully connected to {INTEGRATION_DISPLAY_NAME} service"
        )

        # List IP sets per scope
        for scope in scopes:  # get all existing IP Sets in specified Scope in AWS WAF
            # list existing IP sets in the scope
            ip_sets = [
                ip_set
                for ip_set in waf_client.list_ip_sets(scope=scope)
                if ip_set.name in ip_set_names
            ]
            existing_ip_sets.extend(ip_sets)
            missed_ip_names[scope] = ip_set_names.difference(
                set([ip_set.name for ip_set in ip_sets])
            )

        # At least on of the IP Sets must exist in order to remove IP's from
        if not existing_ip_sets:
            raise AWSWAFNotFoundException(
                f"Failed to find ip set names {', '.join(ip_set_names)} in the {consts.BOTH_SCOPE if len( scopes) == 2 else param_scope} {INTEGRATION_DISPLAY_NAME} service. "
            )

        # Filter supported entity types
        for entity in siemplify.target_entities:
            if entity.entity_type not in SUPPORTED_ENTITIES:
                siemplify.LOGGER.info(
                    f"Entity {entity.identifier} is of unsupported type. Skipping."
                )
                continue
            supported_entities.append(entity)

        if supported_entities:
            # Add entities to IP sets
            for ip_set in existing_ip_sets:
                if is_action_approaching_timeout(siemplify):
                    status = EXECUTION_STATE_TIMEDOUT
                    break

                ips_to_remove = (
                    {}
                )  # key is the masked IP address to add to the IP set, value is the corresponding entity identifier

                try:
                    lock_token, ip_set = waf_client.get_ip_set(
                        scope=ip_set.scope, name=ip_set.name, id=ip_set.ipset_id
                    )

                    # Add all found entities to a single IP Set
                    for entity in supported_entities:  # process entities
                        siemplify.LOGGER.info(
                            f"Started processing entity: {entity.identifier}"
                        )

                        # check if entity entity IP is valid and IP version match IP Set's version
                        if (
                            get_ip_address_version(entity.identifier.strip())
                            != ip_set.ip_version
                        ):
                            failed_ips_in_ipset[ip_set.scoped_name].append(
                                entity.identifier.strip()
                            )
                            siemplify.LOGGER.error(
                                f"Failed to remove IP {entity.identifier} from {ip_set.unmapped_ipversion} IP set {ip_set.name}. Reason: IP {entity.identifier} is invalid or IP version does not match IP Set version."
                            )
                            continue

                        masked_ip = mask_ip_address(
                            entity.identifier
                        )  # check if IP needs to be masked
                        siemplify.LOGGER.info(
                            f"Removing masked IP {masked_ip} from {ip_set.unmapped_ipversion} IP set {ip_set.name}"
                        )

                        ips_to_remove[masked_ip] = entity.identifier.strip()

                    # Check if found entities that exist in the IP Set to remove
                    if ips_to_remove:
                        found_ips_to_remove = [
                            address
                            for address in ip_set.addresses
                            if address in ips_to_remove
                        ]

                        non_existed_ips[ip_set.scoped_name].extend(
                            [
                                ips_to_remove[address]
                                for address in ips_to_remove
                                if address not in ip_set.addresses
                            ]
                        )

                        if found_ips_to_remove:
                            try:
                                siemplify.LOGGER.info(
                                    f"Removing IPs {',  '.join(found_ips_to_remove)} from {ip_set.unmapped_ipversion} "
                                    f"{ip_set.scope} IP set {ip_set.name}"
                                )
                                # Update IP Set with removed ip addresses
                                waf_client.update_ip_set(
                                    scope=ip_set.scope,
                                    name=ip_set.name,
                                    id=ip_set.ipset_id,
                                    # Remove found IP addresses from the IP set
                                    addresses=[
                                        address
                                        for address in ip_set.addresses
                                        if address not in found_ips_to_remove
                                    ],
                                    lock_token=lock_token,
                                )
                                siemplify.LOGGER.info(
                                    f"Successfully removed IPs {',  '.join(found_ips_to_remove)} from {ip_set.unmapped_ipversion} "
                                    f"{ip_set.scope} IP set {ip_set.name}"
                                )
                                successful_ips_in_ipset[ip_set.scoped_name].extend(
                                    [
                                        ips_to_remove[address]
                                        for address in found_ips_to_remove
                                    ]
                                )
                            except Exception as error:
                                failed_ips_in_ipset[ip_set.scoped_name].extend(
                                    [
                                        ips_to_remove[address]
                                        for address in found_ips_to_remove
                                    ]
                                )
                                siemplify.LOGGER.error(
                                    f"Failed to remove IPs {',  '.join(found_ips_to_remove)} from {ip_set.unmapped_ipversion}"
                                    f" {ip_set.unmapped_ipversion} IP set {ip_set.name}. "
                                    f"Reason: {error}"
                                )
                                siemplify.LOGGER.exception(error)

                        else:
                            siemplify.LOGGER.info(
                                f"Didn't find the following IP addresses in {ip_set.unmapped_ipversion} {ip_set.scope} IP Set"
                                f" {ip_set.name} to remove.\n {',   '.join(non_existed_ips[ip_set.scoped_name])}"
                            )

                except (
                    Exception
                ) as error:  # failed to add entities to one of the IP Sets
                    failed_ips_in_ipset[ip_set.scoped_name].extend(
                        [entity.identifier.strip() for entity in supported_entities]
                    )
                    siemplify.LOGGER.error(
                        f"Failed to get  {ip_set.unmapped_ipversion} {ip_set.unmapped_ipversion} IP set {ip_set.name}. "
                        f"Reason: {error}"
                    )
                    siemplify.LOGGER.exception(error)

        # Output message for each IP Set that were found in one of the scopes
        for ip_set in existing_ip_sets:
            # IPs that were successfully added to an IP Set
            if successful_ips_in_ipset.get(ip_set.scoped_name):
                ips = successful_ips_in_ipset.get(ip_set.scoped_name)
                output_message += "\n Successfully removed the following IPs from the {} IP set {} in {}: \n {}".format(
                    ip_set.unmapped_scope,
                    ip_set.name,
                    INTEGRATION_DISPLAY_NAME,
                    "\n  ".join(ips),
                )
                result_value = True

            # IPs that were failing to add to an IP Set
            if failed_ips_in_ipset.get(ip_set.scoped_name):
                ips = failed_ips_in_ipset.get(ip_set.scoped_name)
                output_message += "\n Action was not able to remove the following IPs from {} IP Set {} in {}: \n {}".format(
                    ip_set.unmapped_scope,
                    ip_set.name,
                    INTEGRATION_DISPLAY_NAME,
                    "\n  ".join(ips),
                )

            # IPs that does not exist in the IP Set
            if non_existed_ips.get(ip_set.scoped_name):
                ips = non_existed_ips.get(ip_set.scoped_name)
                output_message += "\n The following IPs were not a part of the {} IP Set {} in {}: \n {}".format(
                    ip_set.unmapped_scope,
                    ip_set.name,
                    INTEGRATION_DISPLAY_NAME,
                    "\n  ".join(ips),
                )

        # Output message if no IP addresses where removed
        if not successful_ips_in_ipset:
            output_message += "\n No IPs were removed from the provided IP Sets."
            result_value = False

        # Output message missing IP Sets
        for scope, ips in missed_ip_names.items():
            if ips:
                output_message += "\n Action wasn't able to find the following {} IP Sets in the {}: \n {}".format(
                    consts.UNMAPPED_SCOPE.get(scope),
                    INTEGRATION_DISPLAY_NAME,
                    "\n   ".join(ips),
                )

    except AWSWAFNotFoundException as error:
        siemplify.LOGGER.error("Action didn't find the provided IP sets.")
        siemplify.LOGGER.exception(error)
        output_message = "Action didn't find the provided IP sets."

    except Exception as error:
        siemplify.LOGGER.error(
            f"Error executing action '{SCRIPT_NAME}'. Reason: {error}"
        )
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        output_message = f"Error executing action '{SCRIPT_NAME}'. Reason: {error}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
