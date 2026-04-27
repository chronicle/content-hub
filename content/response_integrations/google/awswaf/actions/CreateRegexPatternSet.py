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
from soar_sdk.SiemplifyUtils import output_handler, get_domain_from_entity
from ..core.consts import INTEGRATION_NAME, DEFAULT_DDL_SCOPE, HTTP_HTTPS_PROTOCOL_REGEX_WRAP
from ..core.datamodels import RegexSet
from ..core.exceptions import AWSWAFDuplicateItemException, AWSWAFLimitExceededException
from ..core.utils import load_kv_csv_to_dict, is_action_approaching_timeout, get_param_scopes

SCRIPT_NAME = "CreateRegexPatternSet"
SUPPORTED_ENTITIES = (EntityTypes.URL, EntityTypes.ADDRESS)


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

    regex_pattern_set_name = extract_action_param(
        siemplify, param_name="Name", is_mandatory=True, print_value=True
    )

    param_scope = extract_action_param(
        siemplify,
        param_name="Scope",
        is_mandatory=True,
        print_value=True,
        default_value=DEFAULT_DDL_SCOPE,
    )

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

    domain_pattern = extract_action_param(
        siemplify,
        param_name="Domain Pattern",
        is_mandatory=False,
        print_value=True,
        default_value=True,
        input_type=bool,
    )
    ip_pattern = extract_action_param(
        siemplify,
        param_name="IP Pattern",
        is_mandatory=False,
        print_value=True,
        default_value=True,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = "false"
    output_message = ""

    status = EXECUTION_STATE_COMPLETED

    existing_regex_pattern_set = (
        []
    )  # list of Regex Pattern Set datamodels that already exist in AWS WAF
    failed_entities = []  # list of failed entities
    successful_regex_pattern_sets = (
        []
    )  # list of Regex Pattern Set datamodels that were successfully created

    regex_set = None  # regex set to create in AWS WAF

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

        for entity in siemplify.target_entities:  # process entities
            if is_action_approaching_timeout(siemplify):
                status = EXECUTION_STATE_TIMEDOUT
                break

            if entity.entity_type not in SUPPORTED_ENTITIES:
                siemplify.LOGGER.info(
                    f"Entity {entity.identifier} is of unsupported type. Skipping."
                )
                continue

            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")

            regex = entity.identifier

            if domain_pattern and entity.entity_type == EntityTypes.URL:
                domain = get_domain_from_entity(entity)
                regex = HTTP_HTTPS_PROTOCOL_REGEX_WRAP.format(domain)

            elif ip_pattern and entity.entity_type == EntityTypes.ADDRESS:
                regex = HTTP_HTTPS_PROTOCOL_REGEX_WRAP.format(entity.identifier.strip())

            if regex_set:  # regex set created from previous entities
                regex_set.regex_list.append(regex)
                regex_set.entity_list.append(entity.identifier)
            else:  # create new regex set
                regex_set = RegexSet(
                    name=regex_pattern_set_name,
                    regex_list=[regex],
                    entity_list=[entity.identifier],
                )
            siemplify.LOGGER.info(
                f"Created regex {regex} for entity {entity.identifier}"
            )

        if regex_set:  # check if there are regex to create
            if len(regex_set.regex_list) > consts.MAX_REGEX_PATTERNS_IN_REGEX_SET:
                raise AWSWAFLimitExceededException(
                    f"Number of entities to add to Regex Pattern Set exceeds limit of {consts.MAX_REGEX_PATTERNS_IN_REGEX_SET}"
                )
            for (
                scope
            ) in scopes:  # create Regex Pattern Sets for all scopes specified by user
                siemplify.LOGGER.info(
                    f"Creating {scope} Regex Pattern Set {regex_set.name}"
                )
                scoped_regex_set = copy.deepcopy(regex_set)
                scoped_regex_set.scope = scope
                try:
                    created_regex_pattern_set = waf_client.create_regex_pattern_set(
                        name=regex_pattern_set_name,
                        scope=scope,
                        regex_list=regex_set.regex_list,
                        tags=tags,
                        description=description,
                    )
                    siemplify.LOGGER.info(
                        f"Successfully created {scope} Regex Pattern Set {regex_pattern_set_name}"
                    )
                    json_results[consts.UNMAPPED_SCOPE.get(scope)].append(
                        created_regex_pattern_set.name
                    )
                    successful_regex_pattern_sets.append(scoped_regex_set)
                except (
                    AWSWAFDuplicateItemException
                ) as error:  # regex pattern set exists
                    existing_regex_pattern_set.append(scoped_regex_set)
                    siemplify.LOGGER.error(error)
                    siemplify.LOGGER.exception(error)

                except (
                    Exception
                ) as error:  # failed to create Regex Pattern Set in AWS WAF
                    failed_entities += (
                        scoped_regex_set.entity_list
                    )  # failed regex expressions list
                    siemplify.LOGGER.error(error)
                    siemplify.LOGGER.exception(error)
        else:
            output_message = "\n   No Regex Pattern Sets were created. Reason: None of the provided IP/URL entities were valid."

        if existing_regex_pattern_set:
            for regex_set in existing_regex_pattern_set:
                output_message += f"\n {regex_set.unmapped_scope} Regex Pattern Set {regex_set.name} already exist. \n"

        if failed_entities:
            output_message = (
                "\n Action was not able to use the following entities in order to create AWS WAF Regex "
                "Pattern Set: \n {}".format("\n    ".join(set(failed_entities)))
            )

        if successful_regex_pattern_sets:
            for regex_set in successful_regex_pattern_sets:
                output_message += "\n Successfully created {} Regex Pattern Set {} in AWS WAF with the following entities: \n {}".format(
                    regex_set.unmapped_scope,
                    regex_set.name,
                    "\n    ".join(regex_set.entity_list),
                )
            result_value = "true"

    except AWSWAFLimitExceededException as error:
        siemplify.LOGGER.error(
            "Action wasn’t able to create regex pattern sets with all of the provided entities, because the limit is exceeded. The following"
            " entities were skipped: {} ".format("\n    ".join(regex_set.entity_list))
        )
        siemplify.LOGGER.exception(error)
        output_message = (
            "Action wasn’t able to create regex pattern sets with all of the provided entities, because the limit is exceeded. "
            "The following entities were skipped: {} ".format(
                "\n    ".join(regex_set.entity_list)
            )
        )

    except Exception as error:  # action failure that stops a playbook
        siemplify.LOGGER.error(
            f"Error executing action 'Create Regex Pattern Set'. Reason: {error}"
        )
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action 'Create Regex Pattern Set'. Reason: {error}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.result.add_result_json(json_results)
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
