from __future__ import annotations

import json
from typing import Any
from google_threat_intelligence.core import data_models
from google_threat_intelligence.core import api_data_parser as parser
from google_threat_intelligence.core.base_action import BaseAction
from google_threat_intelligence.core.constants import (
    COMPLETED,
    ENRICH_ENTITIES_SCRIPT_NAME,
    ENTITY_TYPE_MAP,
    INTEGRATION_DISPLAY_NAME,
    WIDGET_THEME_MAPPING,
)
from google_threat_intelligence.core.exceptions import (
    EntityNotFoundOrEmptyResults,
    GoogleThreatIntelligenceExceptions,
    ParamsValidationException,
)
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, unix_now
from TIPCommon import validation
from TIPCommon.base.action.data_models import ExecutionState
from TIPCommon.extraction import extract_action_param
from TIPCommon.utils import get_entity_original_identifier
from google_threat_intelligence.core.utils import (
    Enricher,
    assess_risk,
    convert_days_to_milliseconds,
    get_entity_type,
    get_threat_actor_by_origin,
    prepare_entity_for_manager,
)

SUPPORTED_ENTITY_TYPES = [
    EntityTypes.ADDRESS,
    EntityTypes.FILEHASH,
    EntityTypes.CHILDHASH,
    EntityTypes.PARENTHASH,
    EntityTypes.URL,
    EntityTypes.HOSTNAME,
    EntityTypes.DOMAIN,
    EntityTypes.CVE,
    EntityTypes.THREATACTOR,
]

RISK_ASSESSMENT_SUPPORTED = [
    EntityTypes.ADDRESS,
    EntityTypes.FILEHASH,
    EntityTypes.CHILDHASH,
    EntityTypes.PARENTHASH,
    EntityTypes.URL,
    EntityTypes.HOSTNAME,
    EntityTypes.DOMAIN,
]

NOT_SUBMITTABLE_ENTITY_TYPES = [
    EntityTypes.ADDRESS,
    EntityTypes.HOSTNAME,
    EntityTypes.DOMAIN,
    EntityTypes.CVE,
    EntityTypes.THREATACTOR,
]

SUBMITTABLE_ENTITY_TYPES = [
    EntityTypes.FILEHASH,
    EntityTypes.CHILDHASH,
    EntityTypes.PARENTHASH,
    EntityTypes.URL,
]

SUCCESS_MESSAGE = ""
ERROR_MESSAGE = f"Failed to connect to the {INTEGRATION_DISPLAY_NAME} server!"


class EnrichEntities(BaseAction):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self._result_value = self.result_value = True
        self.output_message = SUCCESS_MESSAGE
        self.error_output_message = ERROR_MESSAGE
        self.execution_state = ExecutionState.COMPLETED
        self.json_results = {}
        self.successful_entities = []
        self.failed_entities = []
        self.entities_existing_data = {}
        self.analysis_ids = {}

    def _extract_action_parameters(self) -> None:
        self.params.gti_score = extract_action_param(
            self.soar_action,
            param_name="GTI Score",
            print_value=True,
            input_type=int,
        )

        self.params.engine_threshold = extract_action_param(
            self.soar_action,
            param_name="Engine Threshold",
            print_value=True,
            input_type=int,
        )

        self.params.engine_percentage_threshold = extract_action_param(
            self.soar_action,
            param_name="Engine Percentage Threshold",
            print_value=True,
            input_type=int,
        )

        self.params.engine_allowlist = extract_action_param(
            self.soar_action,
            param_name="Engine Allowlist",
            print_value=True,
            default_value="",
        )

        self.params.resubmit_entity = extract_action_param(
            self.soar_action,
            param_name="Resubmit Entity",
            print_value=True,
            input_type=bool,
        )

        self.params.resubmit_after = extract_action_param(
            self.soar_action,
            param_name="Resubmit After (Days)",
            print_value=True,
            default_value="30",
        )

        self.params.sandbox = extract_action_param(
            self.soar_action,
            param_name="Sandbox",
            print_value=True,
            default_value="VirusTotal Jujubox",
        )

        self.params.retrieve_sandbox_analysis = extract_action_param(
            self.soar_action,
            param_name="Retrieve Sandbox Analysis",
            print_value=True,
            input_type=bool,
        )

        self.params.fetch_mitre_derails = extract_action_param(
            self.soar_action,
            param_name="Fetch MITRE Details",
            print_value=True,
            input_type=bool,
        )

        self.params.lowest_mitre_severity = extract_action_param(
            self.soar_action,
            param_name="Lowest MITRE Technique Severity",
            print_value=True,
            default_value="Medium",
        ).upper()

        self.params.retrieve_comments = extract_action_param(
            self.soar_action,
            param_name="Retrieve Comments",
            print_value=True,
            input_type=bool,
        )

        self.params.max_comments_to_return = extract_action_param(
            self.soar_action,
            param_name="Max Comments To Return",
            print_value=True,
            default_value="10",
        )

        self.params.widget_theme = extract_action_param(
            self.soar_action,
            param_name="Widget Theme",
            print_value=True,
            default_value="Chronicle",
        )

        self.params.additional_data = json.loads(
            extract_action_param(self.soar_action, "additional_data", "{}")
        )

    def _validate_params(self) -> None:
        validator = validation.ParameterValidator(self.soar_action)
        if self.params.gti_score:
            self.params.gti_score = validator.validate_percentage(
                param_name="GTI Score",
                value=self.params.gti_score,
                print_value=False,
            )

        if self.params.engine_threshold:
            self.params.engine_threshold = validator.validate_non_negative(
                param_name="Engine Threshold",
                value=self.params.engine_threshold,
                print_value=False,
            )

        if self.params.engine_percentage_threshold:
            self.params.engine_percentage_threshold = validator.validate_percentage(
                param_name="Engine Percentage Threshold",
                value=self.params.engine_percentage_threshold,
                print_value=False,
            )

        self.params.engine_allowlist = validator.validate_csv(
            param_name="Engine Allowlist",
            csv_string=self.params.engine_allowlist,
            print_value=False,
        )

        if (
            self.params.engine_allowlist
            and self.params.engine_threshold
            and len(self.params.engine_allowlist) < self.params.engine_threshold
        ):
            raise ParamsValidationException(
                "Engine threshold cannot be greater than engine allowlist length"
            )

        self.params.sandbox = validator.validate_csv(
            param_name="Sandbox",
            csv_string=self.params.sandbox,
            print_value=False,
        )
        self.params.max_comments_to_return = validator.validate_positive(
            param_name="Max Comments To Return",
            value=self.params.max_comments_to_return,
            print_value=False,
        )
        self.params.resubmit_after = validator.validate_non_negative(
            param_name="Resubmit After (Days)",
            value=self.params.resubmit_after,
            print_value=False,
        )
        self.params.widget_theme = validator.validate_ddl(
            param_name="Widget Theme",
            value=self.params.widget_theme,
            ddl_values=list(WIDGET_THEME_MAPPING.keys()),
        )

    def _perform_action(self, _: Any = None) -> None:
        """Execute the main logic for enriching entities.
        Filters suitable entities, checks conditions,
        processed them, and store results.

        Args:
            _: Unused argument. Defaults to None.

        """
        initial_ids = self.params.additional_data.get(
            "initial_suitable_entity_identifiers", []
        )
        self.api_client.test_connectivity()

        suitable_entities = self._filter_suitable_entities(
            initial_suitable_entity_identifiers=initial_ids
        )
        if self.is_first_run:
            self._process_first_run(suitable_entities=suitable_entities)
        else:
            self._restore_from_additional_data()
            self._handle_query_or_processing(suitable_entities=suitable_entities)

    def _safe_process_entity(self, entity: Any) -> None:
        """Safely processes a single entity, capturing and logging the exceptions.

        Args:
            entity: The entity object to process.

        """
        try:
            self._process_entity(entity)
        except GoogleThreatIntelligenceExceptions as err:
            self.logger.error(f"Error processing entity {entity.identifier}: {err}")
            self.logger.exception(err)
            self.failed_entities.append(entity.identifier)
            self.entities_existing_data[entity.identifier] = {
                "execution_status": str(err),
            }

    def _process_first_run(self, suitable_entities: list) -> None:
        """Process suitable entities during the first run.
        Filters entities by type, checks resubmission rules,
        processed them and stores the results including
        failed and successful entities.

        Args:
            suitable_entities: Entities considered for processing.

        """
        not_submittable_entities = [
            entity
            for entity in suitable_entities
            if get_entity_type(entity) in NOT_SUBMITTABLE_ENTITY_TYPES
        ]
        submittable_entities = [
            entity
            for entity in suitable_entities
            if get_entity_type(entity) in SUBMITTABLE_ENTITY_TYPES
        ]
        for entity in not_submittable_entities:
            self._safe_process_entity(entity=entity)

        entities_to_resubmit = []
        if self.params.resubmit_entity:
            if self.params.resubmit_after > 0:
                entities_to_resubmit = self._check_resubmission_day(
                    submittable_entities, self.params.resubmit_after
                )
            else:
                entities_to_resubmit = submittable_entities

        if entities_to_resubmit:
            self._process_submittable_entities(entities_to_resubmit)
            if self.analysis_ids:
                result_value = {
                    "entities_existing_data": self.entities_existing_data,
                    "analysis_ids": self.analysis_ids,
                    "initial_suitable_entity_identifiers": [
                        entity.identifier for entity in suitable_entities
                    ],
                    "successful_entities": self.successful_entities,
                    "failed_entities": self.failed_entities,
                }
                self._result_value = json.dumps(result_value)
        else:
            for entity in submittable_entities:
                self._safe_process_entity(entity=entity)
            self._finalize_action(suitable_entities)

    def _restore_from_additional_data(self) -> dict[str, str]:
        """Restore previously saved execution state from additional_data"""
        analysis_ids = self.params.additional_data.get("analysis_ids")
        self.entities_existing_data = self.params.additional_data.get(
            "entities_existing_data"
        )
        self.successful_entities = self.params.additional_data.get(
            "successful_entities"
        )
        self.failed_entities = self.params.additional_data.get("failed_entities")
        return analysis_ids

    def _handle_query_or_processing(self, suitable_entities: list[str]) -> None:
        """Continues processing or querying analysis results
        depending on state.

        Args:
           suitable_entities: List of filtered entities.

        """
        submittable_entities = [
            entity
            for entity in suitable_entities
            if get_entity_type(entity) in SUBMITTABLE_ENTITY_TYPES
        ]
        analysis_ids = self._restore_from_additional_data()
        self._query_operation_status(analysis_ids)
        if self.analysis_ids:
            self.execution_state = ExecutionState.IN_PROGRESS
            result = {
                "entities_existing_data": self.entities_existing_data,
                "analysis_ids": self.analysis_ids,
                "initial_suitable_entity_identifiers": [
                    entity.identifier for entity in suitable_entities
                ],
                "successful_entities": self.successful_entities,
                "failed_entities": self.failed_entities,
            }
            self._result_value = json.dumps(result)

        if not self.analysis_ids:
            for entity in submittable_entities:
                self._safe_process_entity(entity=entity)
            self._finalize_action(suitable_entities=suitable_entities)

    def _query_operation_status(self, task_analysis: dict) -> None:
        """Check analysis status for each entity and
        update the internal state.

        If the status is not COMPLETED, the entity is tracked
        for further processing.
        If an exception occurs, it is logged and the entity
        is marked with the error status.

        Args:
            task_analysis: Mapping of entity to analysis ID.

        """
        for entity, analysis_id in task_analysis.items():
            try:
                status = self.api_client.check_analysis_status(
                    analysis_id, show_entity_status=True
                )
                if status != COMPLETED:
                    self.analysis_ids[entity] = analysis_id
            except GoogleThreatIntelligenceExceptions as e:
                self.entities_existing_data[entity] = {"execution_status": str(e)}
                self.logger.error(
                    f"An error occurred when checking status for url {entity}"
                )
                self.logger.exception(e)
        if self.analysis_ids:
            self.output_message += (
                "Waiting for action to retrieve results for "
                "the following URLs:"
                f"\n{','.join(self.analysis_ids.keys())}"
            )

    def _process_submittable_entities(self, entities_to_resubmit: list[Any]) -> None:
        """Submits entities for analysis and updates the internal state.

        This method iterates through a list of submittable entities,
        submits each one for analysis using the API client, and updates
        the internal state with the results. It handles both successful
        submissions and errors, logging them appropriately.

        Args:
            entities_to_resubmit: A list of entities to submit for analysis.

        """
        self.execution_state = ExecutionState.IN_PROGRESS
        successful_entities = []
        failed_entities = []
        for entity in entities_to_resubmit:
            entity_identifier = get_entity_original_identifier(entity)
            entity_type = get_entity_type(entity)
            self.logger.info(f"Started processing entity {entity_identifier}")

            try:
                if entity_type in [
                    EntityTypes.FILEHASH,
                    EntityTypes.CHILDHASH,
                    EntityTypes.PARENTHASH,
                ]:
                    analysis_id = self.api_client.submit_hash_for_analysis(
                        file_hash=entity_identifier, show_entity_status=True
                    )
                else:
                    analysis_id = self.api_client.submit_url_for_analysis(
                        url=entity_identifier, show_entity_status=True
                    )

                # Fill json with every entity data
                self.analysis_ids[entity_identifier] = analysis_id
                successful_entities.append(entity)
                self.logger.info(f"Finished processing entity {entity_identifier}")

            except GoogleThreatIntelligenceExceptions as e:
                failed_entities.append(entity_identifier)
                self.entities_existing_data[entity_identifier] = {
                    "execution_status": str(e)
                }
                self.logger.error(f"An error occurred on entity {entity_identifier}")
                self.logger.exception(e)

        if successful_entities:
            original_identifiers = [
                get_entity_original_identifier(entity) for entity in successful_entities
            ]
            self.output_message += (
                f"Successfully submitted the following entities "
                f"for analysis: "
                f"\n {', '.join(original_identifiers)} \n"
            )

        if failed_entities:
            self.failed_entities.extend(failed_entities)
            self.output_message += (
                f"Action wasn't able to submitted the following entities for "
                f"analysis: \n {', '.join(failed_entities)} \n"
            )

        if not successful_entities:
            self.execution_state = ExecutionState.COMPLETED

    def _filter_suitable_entities(
        self,
        initial_suitable_entity_identifiers: list[str],
    ) -> list[str]:
        """Filter and return suitable entities based on the current
        execution context.

        If it's the first run, return all target entities whose type is supported.
        Otherwise, return only the entities whose identifiers are in the provided list.

        Args:
            initial_suitable_entity_identifiers:
            Identifiers of suitable entities to retain.

        Returns:
            List: Filtered list of suitable entities.

        """
        target_entities = self._soar_action.target_entities

        if self.is_first_run:
            return [
                entity
                for entity in target_entities
                if get_entity_type(entity) in SUPPORTED_ENTITY_TYPES
            ]
        return [
            entity
            for entity in target_entities
            if entity.identifier in initial_suitable_entity_identifiers
        ]

    def _process_entity(self, entity):
        entity_identifier = get_entity_original_identifier(entity)
        entity_type = get_entity_type(entity)

        if entity_type not in [EntityTypes.THREATACTOR, EntityTypes.CVE]:
            self._process_ioc_entity(entity, entity_identifier)
        elif entity_type == EntityTypes.THREATACTOR:
            self._process_threat_actor_entity(entity_identifier)
        else:
            self._process_cve_entity(entity_identifier)

        self.successful_entities.append(entity_identifier)

    def _process_ioc_entity(self, entity, entity_identifier):
        identifier = prepare_entity_for_manager(entity)
        ioc_type = ENTITY_TYPE_MAP.get(get_entity_type(entity))
        ioc_data = self.api_client.get_ioc_details(
            ioc=identifier, ioc_type=ioc_type, show_entity_status=True
        )

        self.entities_existing_data[entity_identifier] = ioc_data.to_json_shorten(
            get_entity_type(entity)
        )

    def _process_threat_actor_entity(self, entity_identifier):
        entities = self.api_client.get_threat_actor(name=entity_identifier)
        if not entities:
            message: str = "Threat actor entity was not found or empty"
            raise EntityNotFoundOrEmptyResults(message)
        ioc_data = get_threat_actor_by_origin(entities)
        self.entities_existing_data[entity_identifier] = ioc_data.raw_data

    def _process_cve_entity(self, entity_identifier):
        ioc_data = self.api_client.get_vulnerability_details(
            entity_identifier=entity_identifier
        )
        self.entities_existing_data[entity_identifier] = ioc_data.raw_data

    def _check_resubmission_day(
        self,
        suitable_entities: list[str],
        resubmit_days: int,
    ) -> list[str]:
        """Check if the entity should be resubmitted based
        on the last analysis date.

        Args:
            suitable_entities: List of entities to check.
            resubmit_days: Number of days to wait before resubmitting.

        Returns:
            List: Entities that should be resubmitted.

        """
        entities_to_resubmit = []

        for entity in suitable_entities:
            identifier = prepare_entity_for_manager(entity)
            entity_type = get_entity_type(entity)
            ioc_type = ENTITY_TYPE_MAP.get(entity_type)

            entity_identifier = get_entity_original_identifier(entity)
            self.logger.info(
                f"Started checking resubmission day for entity: {entity_identifier}"
            )

            try:
                ioc_data = self.api_client.get_ioc_details(
                    ioc=identifier, ioc_type=ioc_type, show_entity_status=True
                )

                if (
                    unix_now() - convert_days_to_milliseconds(resubmit_days)
                    > ioc_data.last_analysis_date * 1000
                ):
                    entities_to_resubmit.append(entity)
                else:
                    self.entities_existing_data[entity_identifier] = (
                        ioc_data.to_json_shorten(entity_type)
                    )
                    self.successful_entities.append(entity_identifier)

                self.logger.info(
                    f"Finished checking resubmission day for entity {entity_identifier}"
                )

            except GoogleThreatIntelligenceExceptions as err:
                self.logger.error(f"Error processing entity {entity.identifier}: {err}")
                self.logger.exception(err)
                self.failed_entities.append(entity_identifier)
                self.entities_existing_data[entity.identifier] = {
                    "execution_status": str(err),
                }
        return entities_to_resubmit

    def _finalize_action(self, suitable_entities: list[str]) -> None:
        """Finalizes the action by processing all suitable entities,
        updating their properties, and generating the final output.

        Args:
            suitable_entities: List of entities to finalize.

        """
        json_result = {}
        successful_entities = []
        enricher = Enricher(api_client=self.api_client, logger=self.logger)
        for entity in suitable_entities:
            entity_identifier = get_entity_original_identifier(entity)
            entity_type = get_entity_type(entity)
            # Comparing identifier name case sensitive.
            entity_existing_data = self.entities_existing_data.get(entity_identifier)
            try:
                if entity_identifier in self.successful_entities:
                    identifier = prepare_entity_for_manager(entity)
                    if entity_type == EntityTypes.CVE:
                        ioc_data = parser.build_vulnerability_obj(
                            {"data": entity_existing_data}
                        )
                    elif entity_type == EntityTypes.THREATACTOR:
                        ioc_data = parser.build_threat_actor_object(
                            entity_existing_data
                        )
                    else:
                        ioc_type = ENTITY_TYPE_MAP.get(entity_type)
                        ioc_data = parser.build_ioc_object(
                            {"data": entity_existing_data}, ioc_type, identifier
                        )
                    comments, widget_link, widget_html = None, None, None
                    if entity_type not in [EntityTypes.THREATACTOR, EntityTypes.CVE]:
                        if self.params.retrieve_comments:
                            comments = self.api_client.get_comments(
                                ioc_type=ioc_type,
                                ioc=ioc_data.entity_id,
                                limit=self.params.max_comments_to_return,
                                show_entity_status=True,
                            )
                        widget_link, widget_html = self.api_client.get_widget(
                            entity_identifier,
                            theme_colors=WIDGET_THEME_MAPPING.get(
                                self.params.widget_theme
                            ),
                            show_entity_status=True,
                        )
                    should_retrieve_sandbox_analysis: bool = (
                        entity_type
                        in [
                            EntityTypes.FILEHASH,
                            EntityTypes.CHILDHASH,
                            EntityTypes.PARENTHASH,
                        ]
                        and self.params.retrieve_sandbox_analysis
                    )
                    sandboxes_data: dict[str, data_models.Sandbox | None] = (
                        enricher.get_sandbox_response(
                            entity_identifier=entity_identifier,
                            sandboxes=self.params.sandbox,
                        )
                        if should_retrieve_sandbox_analysis
                        else {}
                    )

                    should_fetch_metre_details: bool = (
                        entity_type
                        in [
                            EntityTypes.FILEHASH,
                            EntityTypes.CHILDHASH,
                            EntityTypes.PARENTHASH,
                        ]
                        and self.params.fetch_mitre_derails
                    )
                    mitre_response: data_models.Mitre | None = (
                        enricher.get_mitre_response(
                            entity_identifier=entity_identifier,
                            lowest_mitre_severity=self.params.lowest_mitre_severity,
                        )
                        if should_fetch_metre_details
                        else None
                    )
                    json_result[entity_identifier] = ioc_data.to_json_shorten(
                        entity_type=entity_type,
                        comments=comments,
                        widget_link=widget_link,
                        cached_html_widget=widget_html,
                        sandboxes_data=sandboxes_data,
                        mitre_response=mitre_response,
                    )
                    entity.additional_properties.update(
                        ioc_data.to_enrichment_data(widget_link)
                    )
                    self.logger.info(f"Risk assessment: {entity_identifier}")
                    is_risky = False
                    if entity_type in RISK_ASSESSMENT_SUPPORTED:
                        percentage_threshold = self.params.engine_percentage_threshold
                        is_risky = assess_risk(
                            ioc_data=ioc_data,
                            gti_score=self.params.gti_score,
                            engine_threshold=self.params.engine_threshold,
                            engine_percentage_threshold=percentage_threshold,
                            engine_allowlist=self.params.engine_allowlist,
                            logger=self.logger,
                        )
                        self.logger.info(f"is_risky={is_risky}")
                        entity.is_suspicious = is_risky

                    json_result[entity_identifier].update(
                        {
                            "is_risky": is_risky,
                            "execution_status": "success",
                        }
                    )
                    if ioc_data.report_link:
                        self.soar_action.result.add_entity_link(
                            entity_identifier, ioc_data.report_link
                        )
                    entity.is_enriched = True
                    successful_entities.append(entity)
            except GoogleThreatIntelligenceExceptions as e:
                json_result[entity_identifier] = {"execution_status": str(e)}
                self.logger.error(
                    f"An error occurred when checking status for url {entity}"
                )
                self.logger.exception(e)
                self.failed_entities.append(entity_identifier)
        self.json_results = convert_dict_to_json_result_dict(json_result)
        if successful_entities:
            original_identifiers = [
                get_entity_original_identifier(entity) for entity in successful_entities
            ]
            self.output_message += (
                f"Successfully enriched the "
                f"following entities using  "
                f"{INTEGRATION_DISPLAY_NAME}: \n "
                f"{', '.join(original_identifiers)} \n"
            )
            self.soar_action.update_entities(successful_entities)

        if self.failed_entities:
            self.output_message += (
                f"The action wasn’t able to enrich the "
                f"following entities using "
                f"{INTEGRATION_DISPLAY_NAME}: "
                f"\n {', '.join(self.failed_entities)} \n"
            )

        if not self.successful_entities:
            self.output_message = (
                "The action didn’t enrich any of the provided entities."
            )
            self.result_value = False


def main() -> None:
    """Entry point for executing the EnrichEntities action script.

    This function initialized the EnrichEntities class with
    the predefined script name and triggers its execution.
    """
    EnrichEntities(ENRICH_ENTITIES_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
