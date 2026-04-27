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
from ..core.consts import INTEGRATION_NAME, DEFAULT_DDL_SCOPE
from ..core.exceptions import AWSWAFNotFoundException
from ..core.utils import (
    load_csv_to_set,
    mask_ip_address,
    get_ip_address_version,
    is_action_approaching_timeout,
    get_param_scopes,
)

SCRIPT_NAME = "AddIPToIPSet"
SUPPORTED_ENTITIES = (EntityTypes.ADDRESS,)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
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

    result_value = "false"
    output_message = ""

    supported_entities = []  # list of supported entities of type IP ADDRESS
    successful_ips_in_ipset = defaultdict(
        list
    )  # ips that were successfully added to IP set. Key is IP scoped name, value is list of IPs
    failed_ips_in_ipset = defaultdict(
        list
    )  # ips that failed to add to IP set. Key is IP scoped, value is list of IPS

    status = EXECUTION_STATE_COMPLETED
    waf_ip_sets = []  # list of IP Set data models representing IP Sets in AWS WAF

    try:
        ip_set_names = load_csv_to_set(csv=ip_set_names, param_name="IP Set Names")
        scopes = get_param_scopes(param_scope)

        siemplify.LOGGER.info("Connecting to AWS WAF Service")
        waf_client = AWSWAFManager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_default_region,
        )
        waf_client.test_connectivity()  # this validates the credentials
        siemplify.LOGGER.info("Successfully connected to AWS WAF service")

        for scope in scopes:  # get all existing IP Sets in specified Scope in AWS WAF
            waf_ip_sets += waf_client.list_ip_sets(scope=scope)

        existing_ip_sets = [
            waf_ip_set for waf_ip_set in waf_ip_sets if waf_ip_set.name in ip_set_names
        ]
        missing_ip_set_names = ip_set_names.difference(
            set([ip_set.name for ip_set in existing_ip_sets])
        )

        if not existing_ip_sets:  # at least one ip set name must exist
            raise AWSWAFNotFoundException(
                f"Failed to find ip set names {','.join(ip_set_names)} in the {consts.BOTH_SCOPE if len(scopes) == 2 else param_scope} AWS WAF service. "
            )

        for entity in siemplify.target_entities:  # get supported entities types

            if entity.entity_type not in SUPPORTED_ENTITIES:
                siemplify.LOGGER.info(
                    f"Entity {entity.identifier} is of unsupported type. Skipping."
                )
                continue

            supported_entities.append(entity)

        if supported_entities:
            for ip_set in existing_ip_sets:  # add ip to existing ip set in aws
                if is_action_approaching_timeout(siemplify):
                    status = EXECUTION_STATE_TIMEDOUT
                    break
                masked_ips_to_add = (
                    []
                )  # masked entity IP addresses to add the IP set, with matching IP version
                entity_ips_to_add = (
                    []
                )  # entity IP addresses to add the IP set, with matching IP version
                try:
                    lock_token, ip_set = waf_client.get_ip_set(
                        scope=ip_set.scope, name=ip_set.name, id=ip_set.ipset_id
                    )

                    for entity in supported_entities:  # process entities
                        siemplify.LOGGER.info(
                            f"Started processing entity: {entity.identifier}"
                        )
                        # check if entity IP is valid and IP version match IP Set version
                        if (
                            get_ip_address_version(entity.identifier)
                            != ip_set.ip_version
                        ):
                            failed_ips_in_ipset[ip_set.scoped_name].append(
                                entity.identifier
                            )
                            siemplify.LOGGER.error(
                                f"Failed to add IP {entity.identifier} to {ip_set.unmapped_ipversion} IP set {ip_set.name}. Reason: IP {entity.identifier} is invalid or IP version does not match IP Set version."
                            )
                            continue
                        masked_ip = mask_ip_address(
                            entity.identifier
                        )  # check if IP needs to be masked
                        siemplify.LOGGER.info(
                            f"Adding masked IP {masked_ip} to IP set {ip_set.name}"
                        )
                        masked_ips_to_add.append(masked_ip)
                        entity_ips_to_add.append(entity.identifier)

                    if (
                        masked_ips_to_add
                    ):  # ensure we have new ip addresses to update the IP set with
                        addresses = ip_set.addresses  # existing ip addresses
                        waf_client.update_ip_set(
                            scope=ip_set.scope,
                            name=ip_set.name,
                            id=ip_set.ipset_id,
                            addresses=addresses + masked_ips_to_add,
                            lock_token=lock_token,
                        )
                        siemplify.LOGGER.info(
                            f"Successfully added IPs {', '.join(masked_ips_to_add)} to {ip_set.unmapped_ipversion} {ip_set.scope} IP set {ip_set.name}"
                        )
                        successful_ips_in_ipset[ip_set.scoped_name] += entity_ips_to_add

                except Exception as e:  # failed to add entities to one of the IP Sets
                    failed_ips_in_ipset[ip_set.scoped_name] += supported_entities
                    siemplify.LOGGER.error(
                        f"Failed to add IPs {supported_entities} to IP set {ip_set.name}. Reason: {e}"
                    )
                    siemplify.LOGGER.exception(e)

        for ip_set in existing_ip_sets:  # output message for each IP Set block
            if successful_ips_in_ipset.get(
                ip_set.scoped_name
            ):  # print successful IPs for IP set
                ips = successful_ips_in_ipset.get(ip_set.scoped_name)
                output_message += "\n Successfully added the following IPs to the {} IP set {} in AWS WAF: \n {}".format(
                    ip_set.unmapped_scope, ip_set.name, "\n  ".join(set(ips))
                )
                result_value = "true"

            if failed_ips_in_ipset.get(
                ip_set.scoped_name
            ):  # failed to add IPS to IPSet
                ips = failed_ips_in_ipset.get(ip_set.scoped_name)
                output_message += "\n Action was not able to add the following IPs to the {} IP Set {} in AWS WAF: \n {}".format(
                    ip_set.unmapped_scope, ip_set.name, "\n  ".join(set(ips))
                )

        if not successful_ips_in_ipset:  # check if no ips were added
            output_message += "\n No IPs were added to the provided IP Sets."

        if missing_ip_set_names:
            output_message += "\n Action wasn't able to find the following {} IP Sets in the AWS WAF: \n {}".format(
                consts.BOTH_SCOPE if len(scopes) == 2 else param_scope,
                "\n   ".join(missing_ip_set_names),
            )

    except AWSWAFNotFoundException as error:
        siemplify.LOGGER.error("Action didn't find the provided IP sets.")
        siemplify.LOGGER.exception(error)
        output_message = "Action didn't find the provided IP sets."

    except Exception as error:  # action failure that stops a playbook
        siemplify.LOGGER.error(
            f"Error executing action 'Add IP to IP Set'. Reason: {error}"
        )
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        output_message = f"Error executing action 'Add IP to IP Set'. Reason: {error}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
