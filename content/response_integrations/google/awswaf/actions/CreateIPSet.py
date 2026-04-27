from __future__ import annotations
import copy

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
from ..core.datamodels import IPSet
from ..core.exceptions import AWSWAFDuplicateItemException
from ..core.utils import (
    load_kv_csv_to_dict,
    get_entity_ip_address_version,
    mask_ip_address,
    get_ip_set_full_name,
    is_action_approaching_timeout,
    get_param_scopes,
)

SCRIPT_NAME = "CreateIPSet"
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

    ip_set_name = extract_action_param(
        siemplify, param_name="Name", is_mandatory=True, print_value=True
    )

    scope = extract_action_param(
        siemplify,
        param_name="Scope",
        is_mandatory=True,
        print_value=True,
        default_value=DEFAULT_DDL_SCOPE,
    )
    param_scope = scope  # input param scope
    description = extract_action_param(
        siemplify,
        param_name="Description",
        is_mandatory=False,
        print_value=True,
        default_value=None,
    )
    tags = extract_action_param(
        siemplify,
        param_name="Tags",
        is_mandatory=False,
        print_value=True,
        default_value=None,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = "false"
    output_message = ""

    status = EXECUTION_STATE_COMPLETED

    existing_ip_sets = (
        []
    )  # list of IP Sets names that are duplicates and already exist in WAF.
    failed_entities = []

    # IP Sets to create in AWS WAF. Key is IP Set name + IP version. Value for each key is an IP Set data model.
    ip_sets_to_create = {}

    successful_ip_sets = (
        []
    )  # list of IPSet datamodels that were successfully created on AWS WAF

    json_results = {"Regional": [], "CloudFront": []}

    try:
        tags = load_kv_csv_to_dict(kv_csv=tags, param_name="Tags") if tags else None
        scopes = get_param_scopes(param_scope)

        siemplify.LOGGER.info("Connecting to AWS WAF Service")
        waf_client = AWSWAFManager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_default_region,
        )
        waf_client.test_connectivity()  # this validates the credentials
        siemplify.LOGGER.info("Successfully connected to AWS WAF service")

        for (
            entity
        ) in (
            siemplify.target_entities
        ):  # process entities - mask IP addresses. Append to IPV4 or IPV6 IP Sets.
            if is_action_approaching_timeout(siemplify):
                status = EXECUTION_STATE_TIMEDOUT
                break

            try:
                if entity.entity_type not in SUPPORTED_ENTITIES:
                    siemplify.LOGGER.info(
                        f"Entity {entity.identifier} is of unsupported type. Skipping."
                    )
                    continue
                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")

                ip_version = get_entity_ip_address_version(
                    entity.identifier
                )  # Get IP Version of IP address of entity

                masked_ip = mask_ip_address(entity.identifier)
                ip_set_full_name = get_ip_set_full_name(
                    ip_set_name, ip_version
                )  # Generate IP Set name in format Siemplify_{IP Set Name}_{IP Version}

                ip_set = ip_sets_to_create.get(
                    ip_set_full_name
                )  # Get IP Set with matching ip version

                if (
                    ip_set
                ):  # IP Set already created from previous entities, append address
                    ip_set.addresses.append(masked_ip)
                    ip_set.entity_addresses.append(entity.identifier)
                else:  # create new IP Set for this entity
                    ip_sets_to_create[ip_set_full_name] = IPSet(
                        name=ip_set_full_name,
                        ip_version=ip_version,
                        addresses=[masked_ip],
                        entity_addresses=[entity.identifier],
                    )

            except Exception as error:
                failed_entities.append(entity.identifier)
                siemplify.LOGGER.error(error)
                siemplify.LOGGER.exception(error)

        # create IP Sets
        for ip_set_full_name, ip_set in ip_sets_to_create.items():
            for scope in scopes:  # create IP Sets for all scopes specified by user
                siemplify.LOGGER.info(
                    f"Started creating {scope} IP Sets {ip_set.name} with entities {ip_set.addresses}"
                )
                scoped_ip_set = copy.deepcopy(ip_set)
                scoped_ip_set.scope = scope
                try:
                    created_ip_set = waf_client.create_ip_set(
                        name=ip_set_full_name,
                        scope=scope,
                        ip_version=ip_set.ip_version,
                        addresses=ip_set.addresses,
                        tags=tags,
                        description=description,
                    )
                    siemplify.LOGGER.info(
                        f"Successfully created {scope} IP Set {ip_set_full_name}"
                    )
                    json_results[consts.UNMAPPED_SCOPE.get(scope)].append(
                        created_ip_set.name
                    )
                    successful_ip_sets.append(scoped_ip_set)
                except AWSWAFDuplicateItemException as error:  # ip set exists
                    existing_ip_sets.append(scoped_ip_set)
                    siemplify.LOGGER.error(error)
                    siemplify.LOGGER.exception(error)

                except Exception as error:  # failed to create IP Set in AWS WAF
                    failed_entities += (
                        scoped_ip_set.entity_addresses
                    )  # failed IP addresses
                    siemplify.LOGGER.error(
                        f"An error occurred while creating IP Set {ip_set_full_name}. Reason: {error}"
                    )
                    siemplify.LOGGER.exception(error)

        if existing_ip_sets:
            for ip_set in existing_ip_sets:
                output_message += f"\n The following {ip_set.unmapped_scope} IP Pattern Set {ip_set.name} already exist. \n"

        if successful_ip_sets:  # at least one of the ips were added
            for ip_set in successful_ip_sets:
                output_message += "\n Successfully created {} {} IP Set {} in AWS WAF with the following IPs: \n {}".format(
                    ip_set.unmapped_scope,
                    ip_set.unmapped_ipversion,
                    ip_set.name,
                    "\n  ".join(ip_set.entity_addresses),
                )
            result_value = "true"
        elif not existing_ip_sets:  # all the entities failed
            output_message += "\n   No IP Sets were created. Reason: None of the provided IP entities were valid."

        if (
            failed_entities and successful_ip_sets
        ):  # some of the entities failed, some succeeded
            output_message += "\n Action was not able to use the following IPs in order to create AWS WAF IP Set: \n {}".format(
                "\n   ".join(set(failed_entities))
            )

    except Exception as error:  # action failure that stops a playbook
        siemplify.LOGGER.error(
            f"Error executing action 'Create IP Set'. Reason: {error}"
        )
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        output_message = f"Error executing action 'Create IP Set'. Reason: {error}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.result.add_result_json(json_results)
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
