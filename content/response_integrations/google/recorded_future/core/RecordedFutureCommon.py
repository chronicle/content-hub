# ============================================================================#
# title           :RecordedFutureCommon.py
# description     :This Module contains the logic of the integration
# author          :severins@siemplify.co
# date            :13-10-2019
# python_version  :3.7
# libraries       :json
# requirements    :
# product_version :
# ============================================================================#


# ============================= IMPORTS ===================================== #

from __future__ import annotations
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyUtils import (
    unix_now,
    convert_unixtime_to_datetime,
    convert_dict_to_json_result_dict,
)
from TIPCommon import construct_csv
from .RecordedFutureDataModelTransformationLayer import build_related_entities_report
import json
from .constants import (
    DEFAULT_SCORE,
    SUPPORTED_ENTITY_TYPES_ENRICHMENT,
    SUPPORTED_ENTITY_TYPES_RELATED_ENTITIES,
    PROVIDER_NAME,
)
from .exceptions import RecordedFutureCommonError, RecordedFutureNotFoundError
from .RecordedFutureManager import RecordedFutureManager


class RecordedFutureCommon:
    def __init__(self, siemplify, api_url, api_key, verify_ssl=False):
        self.siemplify = siemplify
        self.api_url = api_url
        self.api_key = api_key
        self.verify_ssl = verify_ssl

    def enrich_common_logic(
        self, entity_types, threshold, script_name, include_related_entities=False
    ):
        """
        Function handles the enrichment of entities.
        :param entity_types: {str} Defines the entity type to filter the entities to process
        :param threshold: {int} Risk Score Threshold
        :param script_name: {str} Script name that identifies the action
        :param include_related_entities: {bool} False if related entities are not returned
        """
        self.siemplify.LOGGER.info("----------------- Main - Started -----------------")

        json_results = {}
        is_risky = False

        try:
            # Initialize manager instance
            recorded_future_manager = RecordedFutureManager(
                self.api_url, self.api_key, verify_ssl=self.verify_ssl
            )
            recorded_future_manager.test_connectivity()

            successful_entities = []
            failed_entities = []
            not_found_entities = []
            output_message = ""
            status = EXECUTION_STATE_COMPLETED

            for entity in self.siemplify.target_entities:
                if unix_now() >= self.siemplify.execution_deadline_unix_time_ms:
                    self.siemplify.LOGGER.error(
                        f"Timed out. execution deadline ({convert_unixtime_to_datetime(self.siemplify.execution_deadline_unix_time_ms)}) has passed"
                    )
                    status = EXECUTION_STATE_TIMEDOUT
                    break

                if entity.entity_type in entity_types:
                    self.siemplify.LOGGER.info(
                        f"Started processing entity: {entity.identifier}"
                    )

                    try:
                        # Host enrichment is a special case in which the entity.identifier has to be modified
                        # This variable is only used to get the entity reputation from the API, for the output the original entity.identifier is used
                        if entity.entity_type == EntityTypes.HOSTNAME:
                            entity_report = recorded_future_manager.get_host_reputation(
                                entity.identifier, include_related_entities
                            )
                        elif entity.entity_type == EntityTypes.CVE:
                            entity_report = recorded_future_manager.get_cve_reputation(
                                entity.identifier, include_related_entities
                            )
                        elif entity.entity_type == EntityTypes.FILEHASH:
                            entity_report = recorded_future_manager.get_hash_reputation(
                                entity.identifier, include_related_entities
                            )
                        elif entity.entity_type == EntityTypes.ADDRESS:
                            entity_report = recorded_future_manager.get_ip_reputation(
                                entity.identifier, include_related_entities
                            )
                        elif entity.entity_type == EntityTypes.URL:
                            entity_report = recorded_future_manager.get_url_reputation(
                                entity.identifier, include_related_entities
                            )
                        else:
                            # This situation can only happen for custom actions and in case a user will put some entity type that the Recorded Future can't enrich such as EntityType.FILE.
                            raise RecordedFutureCommonError(
                                "Given entity type: {} can't be enriched by Recorded "
                                "Future. Please choose one of the following entity types: "
                                "{}".format(
                                    entity.entity_type,
                                    ",".join(SUPPORTED_ENTITY_TYPES_ENRICHMENT),
                                )
                            )

                        json_results[entity.identifier] = entity_report.raw_data
                        self.siemplify.result.add_data_table(
                            title=f"Report for: {entity.identifier}",
                            data_table=construct_csv(entity_report.to_table()),
                        )

                        if include_related_entities and entity_report.related_entities:
                            self.siemplify.result.add_data_table(
                                title=f"Related Entities For: {entity.identifier}",
                                data_table=construct_csv(
                                    [
                                        related_entity.to_table()
                                        for related_entity in entity_report.related_entities
                                    ]
                                ),
                            )
                        enrichment_data = entity_report.to_enrichment_data()

                        score = entity_report.score
                        if not score:
                            # If there is no score in the report, the default score will be used
                            score = DEFAULT_SCORE
                            self.siemplify.LOGGER.info(
                                "There is no score for the entity {}, the default score: "
                                "{} will be used.".format(
                                    entity.identifier, DEFAULT_SCORE
                                )
                            )

                        if int(score) > threshold:
                            entity.is_suspicious = True
                            is_risky = True
                            self.siemplify.create_case_insight(
                                PROVIDER_NAME,
                                "Enriched by Reported Future",
                                self.get_insight_content(
                                    entity_report, enrichment_data, threshold
                                ),
                                entity.identifier,
                                1,
                                1,
                            )

                        if entity_report.intelCard is not None:
                            self.siemplify.result.add_link(
                                "Web Report Link: ", entity_report.intelCard
                            )

                        entity.additional_properties.update(enrichment_data)
                        entity.is_enriched = True
                        entity.is_risky = is_risky
                        successful_entities.append(entity)
                        self.siemplify.LOGGER.info(
                            f"Finished processing entity {entity.identifier}"
                        )
                    except RecordedFutureNotFoundError as e:
                        not_found_entities.append(entity)
                        self.siemplify.LOGGER.error(
                            f"An 404 error occurred on entity {entity.identifier}"
                        )
                        self.siemplify.LOGGER.exception(e)
                    except Exception as e:
                        failed_entities.append(entity)
                        self.siemplify.LOGGER.error(
                            f"An error occurred on entity {entity.identifier}"
                        )
                        self.siemplify.LOGGER.exception(e)

            if successful_entities:
                entities_names = [entity.identifier for entity in successful_entities]
                output_message += "Successfully processed entities: \n{}\n".format(
                    "\n".join(entities_names)
                )

                self.siemplify.update_entities(successful_entities)

            if not_found_entities:
                output_message += (
                    "Failed to process entities - either endpoint could not be found successfully"
                    " or action was not able to find the following entities in Recorded future's server: "
                    "\n{}\n".format(
                        "\n".join([entity.identifier for entity in not_found_entities])
                    )
                )

            if failed_entities:
                output_message += "Failed processing entities: \n{}\n".format(
                    "\n".join([entity.identifier for entity in failed_entities])
                )

            if (
                not failed_entities
                and not not_found_entities
                and not successful_entities
            ):
                output_message = "No entities were enriched."

        except Exception as e:
            self.siemplify.LOGGER.error(
                f"General error performing action {script_name}"
            )
            self.siemplify.LOGGER.exception(e)
            status = EXECUTION_STATE_FAILED
            output_message = f"An error occurred while running action: {e}"

        self.siemplify.LOGGER.info(
            "----------------- Main - Finished -----------------"
        )
        self.siemplify.LOGGER.info(
            f"\nstatus: {status}\nis_risky: {is_risky}\noutput_message: {output_message}"
        )
        self.siemplify.result.add_result_json(
            convert_dict_to_json_result_dict(json_results)
        )
        self.siemplify.end(output_message, is_risky, status)

    def get_related_entities_logic(self, entity_types, script_name):
        """
        Function handles the related entities of given entities.
        :param entity_types: {str} Defines the entity type to filter the entities to process
        :param script_name: {str} Script name that identifies the action
        """
        self.siemplify.LOGGER.info("----------------- Main - Started -----------------")
        result_value = False

        try:
            # Initialize manager instance
            recorded_future_manager = RecordedFutureManager(
                self.api_url, self.api_key, verify_ssl=self.verify_ssl
            )
            recorded_future_manager.test_connectivity()

            successful_entities = []
            failed_entities = []
            not_found_entities = []
            output_message = ""
            status = EXECUTION_STATE_COMPLETED

            for entity in self.siemplify.target_entities:
                if unix_now() >= self.siemplify.execution_deadline_unix_time_ms:
                    self.siemplify.LOGGER.error(
                        f"Timed out. execution deadline ({convert_unixtime_to_datetime(self.siemplify.execution_deadline_unix_time_ms)}) has passed"
                    )
                    status = EXECUTION_STATE_TIMEDOUT
                    break

                if entity.entity_type in entity_types:
                    self.siemplify.LOGGER.info(
                        f"Started processing entity: {entity.identifier}"
                    )

                    try:
                        if entity.entity_type == EntityTypes.HOSTNAME:
                            entity_report = (
                                recorded_future_manager.get_host_related_entities(
                                    entity.identifier
                                )
                            )
                        elif entity.entity_type == EntityTypes.CVE:
                            entity_report = (
                                recorded_future_manager.get_cve_related_entities(
                                    entity.identifier
                                )
                            )
                        elif entity.entity_type == EntityTypes.FILEHASH:
                            entity_report = (
                                recorded_future_manager.get_hash_related_entities(
                                    entity.identifier
                                )
                            )
                        elif entity.entity_type == EntityTypes.ADDRESS:
                            entity_report = (
                                recorded_future_manager.get_ip_related_entities(
                                    entity.identifier
                                )
                            )
                        else:
                            # This situation can only happen for custom actions and in case a user will put some entity type that the Recorded Future can't enrich such as EntityType.FILE.
                            raise RecordedFutureCommonError(
                                "Given entity type: {} can't be enriched by Recorded "
                                "Future. Please choose one of the following entity types: "
                                "{}".format(
                                    entity.entity_type,
                                    ",".join(SUPPORTED_ENTITY_TYPES_RELATED_ENTITIES),
                                )
                            )

                        result_value = True
                        related_entities_report = build_related_entities_report(
                            entity_report
                        )
                        self.siemplify.result.add_json(
                            f"Related Entities for: {entity.identifier}",
                            json.dumps(related_entities_report),
                        )

                        successful_entities.append(entity)
                        if entity_report.intelCard:
                            self.siemplify.result.add_link(
                                "Web Report Link: ", entity_report.intelCard
                            )
                    except RecordedFutureNotFoundError as e:
                        not_found_entities.append(entity)
                        self.siemplify.LOGGER.error(
                            f"An 404 error occurred on entity {entity.identifier}"
                        )
                        self.siemplify.LOGGER.exception(e)
                    except Exception as e:
                        failed_entities.append(entity)
                        self.siemplify.LOGGER.error(
                            f"An error occurred on entity {entity.identifier}"
                        )
                        self.siemplify.LOGGER.exception(e)

            if successful_entities:
                entities_names = [entity.identifier for entity in successful_entities]
                output_message += "Successfully processed entities: \n{}\n".format(
                    "\n".join(entities_names)
                )

                self.siemplify.update_entities(successful_entities)

            if not_found_entities:
                output_message += (
                    "Failed to process entities - either endpoint could not be found successfully"
                    " or action was not able to find the following entities in Recorded future's "
                    "server: \n{}\n".format(
                        "\n".join([entity.identifier for entity in not_found_entities])
                    )
                )

            if failed_entities:
                output_message += "Failed processing entities: \n{}\n".format(
                    "\n".join([entity.identifier for entity in failed_entities])
                )

            if (
                not failed_entities
                and not not_found_entities
                and not successful_entities
            ):
                output_message = "No entities were enriched."

        except Exception as e:
            self.siemplify.LOGGER.error(
                f"General error performing action {script_name}"
            )
            self.siemplify.LOGGER.exception(e)
            status = EXECUTION_STATE_FAILED
            output_message = f"An error occurred while running action: {e}"

        self.siemplify.LOGGER.info(
            "----------------- Main - Finished -----------------"
        )
        self.siemplify.LOGGER.info(
            f"\nstatus: {status}\nresult_value: {result_value}\noutput_message: {output_message}"
        )
        self.siemplify.end(output_message, result_value, status)

    def get_insight_content(self, data, enrichment_data, threshold):
        """
        Prepare insight content string
        :param data: The entity report data
        :param enrichment_data: The entity report enrichment data
        :param threshold: {int} Risk score threshold
        :return: {str} The insight content string
        """
        content = ""
        content += (
            f"Entity was marked malicious with {enrichment_data.get('RF_RiskString', {})} rules triggered. "
            if enrichment_data.get("RF_RiskString", {})
            else ""
        )
        content += f"Entity score was {data.score}. " if data.score else ""
        content += f"Threshold was set to {threshold}. " if threshold else ""
        content += (
            f"Triggered rule names are {','.join(rule_name for rule_name in data.rule_names)}. "
            if data.rule_names
            else ""
        )
        content += (
            f"Link to Recorder Future's web report is {data.intelCard}."
            if data.intelCard
            else ""
        )

        return content
