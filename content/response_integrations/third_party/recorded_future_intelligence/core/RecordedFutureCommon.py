############################## TERMS OF USE ################################### # noqa: E266
# The following code is provided for demonstration purposes only, and should  #
# not be used without independent verification. Recorded Future makes no      #
# representations or warranties, express, implied, statutory, or otherwise,   #
# regarding this code, and provides it strictly "as-is".                      #
# Recorded Future shall not be liable for, and you assume all risk of         #
# using the foregoing.                                                        #
###############################################################################

# ============================================================================#
# title           :RecordedFutureCommon.py                          noqa: ERA001
# description     :This Module contains the logic of the integration
# author          :support@recordedfuture.com                       noqa: ERA001
# date            :10-31-2025
# python_version  :3.11                                             noqa: ERA001
# product_version :8.0
# ============================================================================#


# ============================= IMPORTS ===================================== #

from __future__ import annotations

import typing

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    convert_dict_to_json_result_dict,
    convert_unixtime_to_datetime,
    unix_now,
)
from TIPCommon.smp_time import is_approaching_timeout
from TIPCommon.transformation import construct_csv
from triage import Client
from UtilsManager import (
    format_timestamp,
    is_async_action_global_timeout_approaching,
)

from .constants import (
    DEFAULT_SCORE,
    DEFAULT_TIMEOUT,
    INVALID_SAMPLE_TEXT,
    PROVIDER_NAME,
    SUPPORTED_ENTITY_TYPES_ENRICHMENT,
)
from .datamodels import IP
from .exceptions import (
    RecordedFutureCommonError,
    RecordedFutureNotFoundError,
    SandboxTimeoutError,
)
from .RecordedFutureManager import RecordedFutureManager


def _list(data: list):
    if not data:
        return ""

    content = ["<ul>"]
    content.extend(f"<li>{elem}</li>" for elem in data)
    content.append("</ul>")
    return "".join(content)


def _title_and_content(title, content):
    """Return bold title, columns and content."""
    return f"<strong>{title}:</strong> {content}</br>"


def _title(title):
    return f"</br><h2>{title}:</h2></br>"


def _subtitle(title):
    return f"<h3>{title}</h3>"


class RecordedFutureCommon:
    """Recorded Future Common."""

    def __init__(self, siemplify, api_url, api_key, verify_ssl=False):
        self.siemplify = siemplify
        self.api_url = api_url
        self.api_key = api_key
        self.verify_ssl = verify_ssl

    def enrich_common_logic(
        self,
        entity_types,
        threshold,
        script_name,
        include_links=False,
        collective_insights_enabled=True,
    ):
        """Function handles the enrichment of entities.
        :param entity_types: {list} Defines the entity type to filter the entities to process
        :param threshold: {int} Risk Score Threshold
        :param script_name: {str} Script name that identifies the action
        :param include_links: {bool} Defines if links are returned
        :param collective_insights_enabled {bool} True when Collective Insights should be submitted.
        """
        self.siemplify.LOGGER.info("----------------- Main - Started -----------------")

        json_results = {}
        is_risky = False

        try:
            # Initialize manager instance
            recorded_future_manager = RecordedFutureManager(
                self.api_url,
                self.api_key,
                verify_ssl=self.verify_ssl,
                siemplify=self.siemplify,
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
                        "Timed out. execution deadline ({}) has passed".format(
                            convert_unixtime_to_datetime(
                                self.siemplify.execution_deadline_unix_time_ms,
                            ),
                        ),
                    )
                    status = EXECUTION_STATE_TIMEDOUT
                    break

                if entity.entity_type in entity_types:
                    self.siemplify.LOGGER.info(
                        f"Started processing entity: {entity.identifier}",
                    )

                    try:
                        if entity.entity_type in (
                            EntityTypes.HOSTNAME,
                            EntityTypes.DOMAIN,
                        ):
                            entity_id = entity.identifier.lower()
                            entity_report = recorded_future_manager.get_host_reputation(
                                entity_id,
                                include_links,
                                collective_insights_enabled,
                            )
                        elif entity.entity_type == EntityTypes.CVE:
                            entity_id = entity.identifier.upper()
                            entity_report = recorded_future_manager.get_cve_reputation(
                                entity_id,
                                include_links,
                                collective_insights_enabled,
                            )
                        elif entity.entity_type == EntityTypes.FILEHASH:
                            entity_id = entity.identifier.lower()
                            entity_report = recorded_future_manager.get_hash_reputation(
                                entity_id,
                                include_links,
                                collective_insights_enabled,
                            )
                        elif entity.entity_type == EntityTypes.ADDRESS:
                            entity_report = recorded_future_manager.get_ip_reputation(
                                entity.identifier,
                                include_links,
                                collective_insights_enabled,
                            )
                        elif entity.entity_type == EntityTypes.URL:
                            entity_id = entity.identifier.lower()
                            entity_report = recorded_future_manager.get_url_reputation(
                                entity_id,
                                include_links,
                                collective_insights_enabled,
                            )
                        else:
                            raise RecordedFutureCommonError(
                                "Given entity type: {} can't be enriched by Recorded "
                                "Future. Please choose one of the following entity types: "
                                "{}".format(
                                    entity.entity_type,
                                    ",".join(SUPPORTED_ENTITY_TYPES_ENRICHMENT),
                                ),
                            )

                        json_results[entity.identifier] = entity_report.to_json()
                        self.siemplify.result.add_data_table(
                            title=f"Report for: {entity.identifier}",
                            data_table=construct_csv(entity_report.to_overview_table()),
                        )
                        self.siemplify.result.add_data_table(
                            title=f"Triggered Risk Rules for: {entity.identifier}",
                            data_table=construct_csv(entity_report.to_risk_table()),
                        )

                        if include_links and entity_report.links:
                            self.siemplify.result.add_data_table(
                                title=f"Links For: {entity.identifier}",
                                data_table=construct_csv(
                                    entity_report.to_links_table(),
                                ),
                            )
                        enrichment_data = entity_report.to_enrichment_data()

                        score = entity_report.score
                        if not score:
                            # If there is no score in the report, the default score will be used
                            score = DEFAULT_SCORE
                            self.siemplify.LOGGER.info(
                                f"There is no score for the entity {entity.identifier}, "
                                f"the default score: {DEFAULT_SCORE} will be used.",
                            )

                        if int(score) > threshold:
                            entity.is_suspicious = True
                            is_risky = True
                            self.siemplify.create_case_insight(
                                PROVIDER_NAME,
                                "Enriched by Reported Future",
                                self.get_insight_content(
                                    entity_report,
                                    enrichment_data,
                                ),
                                entity.identifier,
                                1,
                                1,
                            )

                        if entity_report.intelCard is not None:
                            self.siemplify.result.add_link(
                                f"Web Report Link for {entity.identifier}: ",
                                entity_report.intelCard,
                            )

                        entity.additional_properties.update(enrichment_data)
                        entity.is_enriched = True
                        entity.is_risky = is_risky
                        successful_entities.append(entity)
                        self.siemplify.LOGGER.info(
                            f"Finished processing entity {entity.identifier}",
                        )
                    except RecordedFutureNotFoundError as e:
                        not_found_entities.append(entity)
                        self.siemplify.LOGGER.error(
                            f"An 404 error occurred on entity {entity.identifier}",
                        )
                        self.siemplify.LOGGER.exception(e)
                    except Exception as e:
                        failed_entities.append(entity)
                        self.siemplify.LOGGER.error(
                            f"An error occurred on entity {entity.identifier}",
                        )
                        self.siemplify.LOGGER.exception(e)

            if successful_entities:
                entities_names = [entity.identifier for entity in successful_entities]
                output_message += "Successfully processed entities: \n{}\n".format(
                    "\n".join(entities_names),
                )

                self.siemplify.update_entities(successful_entities)

            if not_found_entities:
                output_message += (
                    "Failed to process entities - either endpoint could not be found successfully"
                    "or action was not able to find the "
                    "following entities in Recorded future's server: "
                    "\n{}\n".format(
                        "\n".join([entity.identifier for entity in not_found_entities]),
                    )
                )

            if failed_entities:
                output_message += "Failed processing entities: \n{}\n".format(
                    "\n".join([entity.identifier for entity in failed_entities]),
                )

            if (
                not failed_entities
                and not not_found_entities
                and not successful_entities
            ):
                output_message = "No entities were enriched."

        except Exception as e:
            self.siemplify.LOGGER.error(
                f"General error performing action {script_name}",
            )
            self.siemplify.LOGGER.exception(e)
            status = EXECUTION_STATE_FAILED
            output_message = f"An error occurred while running action: {e}"

        self.siemplify.LOGGER.info(
            "----------------- Main - Finished -----------------",
        )
        self.siemplify.LOGGER.info(
            f"\nstatus: {status}\nis_risky: {is_risky}\noutput_message: {output_message}",
        )
        self.siemplify.result.add_result_json(
            convert_dict_to_json_result_dict(json_results),
        )
        self.siemplify.end(output_message, is_risky, status)

    def get_insight_content(self, entity_report, enrichment_data):
        """Prepare insight content string as HTML
        :param entity_report: The entity report data
        :param enrichment_data: The entity report enrichment data
        :return: {str} The insight content string.
        """
        content = ""

        evidence_details = (
            entity_report.raw_data[0].get("risk", {}).get("evidenceDetails")
            if entity_report.raw_data
            else []
        )
        evidence_details.sort(key=lambda y: y["criticality"], reverse=True)

        if enrichment_data.get("RF_RiskString", {}):
            s = enrichment_data["RF_RiskString"]
            content += f"<p>Entity was marked malicious with {s} rules triggered.</p>"

        content += _subtitle(f"Risk Score: {entity_report.score or 0}")

        if entity_report.intelCard:
            msg = (
                "Link to Recorded Future portal: <a href='{0}' target='_blank'>{0}</a>"
            )
            content += f"<p></br>{msg.format(entity_report.intelCard)}</p></br>"

        if isinstance(entity_report, IP):
            content += self._add_location_data(entity_report)

        content += _title("Risk Details")
        content += self._add_evidence_data(evidence_details)
        return content

    def _add_evidence_data(self, evidence_details):
        content = ""
        for details in evidence_details:
            formatted_timestamp = format_timestamp(details.get("timestamp"))

            content += _subtitle(details["rule"])
            content += _title_and_content("Timestamp", formatted_timestamp)
            content += _title_and_content("Criticality", details["criticalityLabel"])
            content += _title_and_content("Evidence", details["evidenceString"])
            content += "<hr>"
        return content

    def _add_location_data(self, entity_report):
        content = ""
        if any(
            _
            for _ in [
                entity_report.city,
                entity_report.country,
                entity_report.organization,
            ]
        ):
            content += _title("Location Details")
            if entity_report.country:
                content += _title_and_content("Country", entity_report.country)
            if entity_report.city:
                content += _title_and_content("City", entity_report.city)
            if entity_report.organization:
                content += _title_and_content(
                    "Organization",
                    entity_report.organization,
                )
        return content


class RecordedFutureSandboxCommon:
    """Recorded Future Sandbox Common."""

    def __init__(
        self,
        siemplify,
        sandbox_url,
        sandbox_api_key,
        action_context,
        start_time,
        profile=None,
        password=None,
    ):
        self.siemplify = siemplify
        self.sandbox_url = sandbox_url
        self.sandbox_api_key = sandbox_api_key
        self.action_context = action_context
        self.start_time = start_time
        self.profile = self._format_profile(profile)
        self.password = password

    @property
    def triage_client(self):
        """Hatching Triage Client."""
        root = f"{self.sandbox_url}/api"
        return Client(token=self.sandbox_api_key, root_url=root)

    def query_status(self):
        """Updates Action Context for samples submitted to the Sandbox."""
        pending_submissions_data = {
            entity_name: submission_data
            for entity_name, submission_data in self.action_context[
                "submissions"
            ].items()
            if submission_data.get("pending_submissions", [])
        }

        self.check_timeout()

        if not pending_submissions_data:
            return True

        submissions_map = {}

        for entity_name, submission_data in pending_submissions_data.items():
            submissions_map.update(
                dict.fromkeys(submission_data["pending_submissions"], entity_name),
            )

        submissions_data = []
        for sample_id in list(submissions_map.keys()):
            sample_status = self.fetch_sample_by_id(sample_id)
            submissions_data.append(sample_status)

        finished_submissions = []
        failed_submissions = []

        # Process submissions data
        for submission in submissions_data:
            sample_id = submission["id"]
            sample_status = submission["status"]
            self.siemplify.LOGGER.info(
                f"Submissions state for {submissions_map[sample_id]} - {sample_status}",
            )
            if sample_status == "reported":
                finished_submissions.append(submission)
            elif sample_status == "failed":  # TODO what's actual fail status
                failed_submissions.append(submission)

        self.check_timeout()

        # Handle finished submissions
        self.siemplify.LOGGER.info(
            "Getting submission reports for finished submissions ...",
        )
        finished_sample_ids = [sample["id"] for sample in finished_submissions]
        sample_reports = []
        for sample_id in finished_sample_ids:
            overview_report = self.fetch_overview_report(sample_id)
            sample_reports.append(overview_report)

        for sample_report in sample_reports:
            sample_id = sample_report["sample"]["id"]
            sample_target = sample_report["sample"]["target"]
            self.siemplify.LOGGER.info(
                f"Submission {sample_id} for {sample_target} is fully processed.",
            )
            self.action_context["submissions"][sample_target][
                "pending_submissions"
            ].remove(sample_id)

            reports = self.action_context["submissions"][sample_target].get(
                "finished_submissions",
                [],
            )
            reports.append(sample_report)
            self.action_context["submissions"][sample_target][
                "finished_submissions"
            ] = reports

        # Handle failed submissions
        for submission_data in failed_submissions:
            entity_name = submissions_map[submission_data.id]
            self.siemplify.LOGGER.info(
                f"Submission for {submission_data.id} have failed.",
            )
            self.action_context["submissions"][sample_target][
                "pending_submissions"
            ].remove(submission_data.id)

            failed_submissions = self.action_context["submissions"][entity_name].get(
                "failed_submissions",
                [],
            )
            failed_submissions.append(submission_data.get_entity_name())
            self.action_context["submissions"][entity_name]["failed_submissions"] = (
                failed_submissions
            )

        # Return is the process finished for all pending submissions
        return self.is_all_reported()

    def is_all_reported(self):
        """Checks if all samples are reported in the Sandbox."""
        return all(
            not (submission_data["pending_submissions"])
            for submission_data in self.action_context["submissions"].values()
        )

    def check_timeout(self):
        """Checks if the Action is timed out."""
        timed_out = is_approaching_timeout(
            self.start_time,
            DEFAULT_TIMEOUT,
        ) or is_async_action_global_timeout_approaching(self.siemplify, self.start_time)
        if timed_out:
            error_message = self.get_timeout_error_message()
            raise SandboxTimeoutError(error_message)

    def get_timeout_error_message(self):
        """Generates a timeout message."""
        pending_entities = (
            entity_name
            for entity_name, submission in self.action_context["submissions"].items()
            if submission.get("pending_submissions", [])
        )
        return (
            f"action ran into a timeout during execution. Pending files: "
            f"{', '.join(pending_entities)}. Please increase the timeout in IDE."
        )

    def submit_sample_url(self, url: str):
        """Helper method to submit URL to the Sandbox."""
        return self.triage_client.submit_sample_url(url, profiles=self.profile)

    def submit_sample_file(self, filename: str, file: typing.BinaryIO):
        """Submits File for detonation."""
        return self.triage_client.submit_sample_file(
            filename,
            file,
            profiles=self.profile,
            password=self.password,
        )

    def fetch_sample_by_id(self, sample_id: str):
        """Helper method to fetch sample status from the Sandbox by ID."""
        return self.triage_client.sample_by_id(sample_id)

    def fetch_overview_report(self, sample_id: str):
        """Helper method to fetch overview report from the Sandbox by ID."""
        return self.triage_client.overview_report(sample_id)

    def add_insights(self):
        """Add HTML insights to GSOAR case."""
        for entity_name, submissions in self.action_context["submissions"].items():
            for report in submissions.get("finished_submissions", []):
                self._add_insight(report, entity_name)

    def detonation_html(self, data) -> str:
        """HTML of detonation report."""
        sample = data.get("sample", {})
        if not sample:
            return INVALID_SAMPLE_TEXT

        content = [
            _title("Recorded Future Sandbox Detonation Details"),
            _subtitle("Summary"),
            _title_and_content(
                "Score",
                "{}/10".format(data.get("analysis", {}).get("score", 0)),
            ),
            _title_and_content(
                "Scan Created",
                sample.get("created", "").replace("T", " ").rstrip("Z"),
            ),
            _title_and_content(
                "Scan Completed",
                sample.get("completed", "").replace("T", " ").rstrip("Z"),
            ),
            _title_and_content("Initial Scan Target", sample.get("target")),
            _title_and_content(
                "Scan URL",
                f"https://sandbox.recordedfuture.com/{sample.get('id')}",  # TODO base URL
            ),
            "<hr>",
            _title_and_content("Tags", ", ".join(tags))
            if (tags := data.get("analysis", {}).get("tags", []))
            else "",
        ]

        if signatures := self._get_signatures(data):
            content.append(_subtitle("Signatures"))
            content.extend(signatures)
            content.append("<hr>")

        targets = []
        if not (targets_data := data.get("targets", [])):
            return "".join(content)

        targets.append(_subtitle("Targets"))
        for target_data in targets_data:
            target = _title_and_content("Target Name", target_data.get("target"))
            score = _title_and_content(
                "Target Score",
                f"{target_data.get('score', 0)}/10",
            )

            targets.extend([target, score])

            if not (iocs := target_data.get("iocs", {})):
                continue

            iocs = {k.title(): v for k, v in iocs.items()}
            if iocs.get("Ips"):
                iocs["IPs"] = iocs["Ips"]
                del iocs["Ips"]

            transformed_iocs = {}
            for k, ioc_list in iocs.items():
                new_key = k.title()
                if new_key == "Ips":
                    new_key = "IPs"

                transformed_iocs[new_key] = sorted(
                    {item.split("?")[0] for item in ioc_list},
                )

            targets.extend(
                _title_and_content(k, _list(v) + "</br>")
                for k, v in transformed_iocs.items()
            )

        if targets:
            content.extend(targets)

        return "".join(content)

    def _get_signatures(self, data):
        """Extract and format signatures from report."""
        signature_data = data.get("signatures", [])
        if not signature_data:
            return ""

        html = ""
        for sign in signature_data:
            name = (
                _title_and_content("Name", s_name)
                if (s_name := sign.get("name", ""))
                else ""
            )
            score = _title_and_content("Score", sign.get("score", 0))
            ttp = (
                _title_and_content("TTP", ", ".join(s_ttp))
                if (s_ttp := sign.get("ttp", []))
                else ""
            )
            html += f"{name}{score}{ttp}</br>"

        return html

    def _format_profile(self, profile: str = None):
        if profile is None:
            return None
        return [{"profile": profile}]
