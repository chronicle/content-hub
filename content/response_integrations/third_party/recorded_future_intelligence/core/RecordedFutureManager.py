############################## TERMS OF USE ################################### # noqa: E266
# The following code is provided for demonstration purposes only, and should  #
# not be used without independent verification. Recorded Future makes no      #
# representations or warranties, express, implied, statutory, or otherwise,   #
# regarding this code, and provides it strictly "as-is".                      #
# Recorded Future shall not be liable for, and you assume all risk of         #
# using the foregoing.                                                        #
###############################################################################

# ============================================================================#
# title           :RecordedFutureManager.py                         noqa: ERA001
# description     :This Module contains all Recorded Future operations functionality
# author          :support@recordedfuture.com                       noqa: ERA001
# date            :10-31-2025
# python_version  :3.11                                             noqa: ERA001
# product_version :8.0
# ============================================================================#

# ============================= IMPORTS ===================================== #

from __future__ import annotations

from datetime import datetime

from psengine.analyst_notes import AnalystNoteMgr, AnalystNotePublishError
from psengine.classic_alerts import (
    AlertFetchError,
    AlertSearchError,
    AlertUpdateError,
    ClassicAlertMgr,
)
from psengine.collective_insights import (
    CollectiveInsights,
    CollectiveInsightsError,
)
from psengine.config import Config
from psengine.enrich import EnrichmentLookupError, LookupMgr
from psengine.playbook_alerts import (
    PBA_DomainAbuse,
    PBA_IdentityNovelExposure,
    PlaybookAlertFetchError,
    PlaybookAlertMgr,
    PlaybookAlertUpdateError,
)
from pydantic import ValidationError
from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon.filters import filter_old_alerts

from .constants import (
    ALERT_ID_FIELD,
    CLASSIC_ALERT_DEFAULT_STATUSES,
    CONNECTOR_DATETIME_FORMAT,
    ENTITY_PREFIX_TYPE_MAP,
    PLAYBOOK_ALERT_API_LIMIT,
)
from .exceptions import (
    RecordedFutureDataModelTransformationLayerError,
    RecordedFutureManagerError,
    RecordedFutureNotFoundError,
)
from .RecordedFutureDataModelTransformationLayer import (
    build_alert,
    build_playbook_alert,
    build_siemplify_alert_object,
    build_siemplify_analyst_note_object,
    build_siemplify_cve_object,
    build_siemplify_hash_object,
    build_siemplify_host_object,
    build_siemplify_ip_object,
    build_siemplify_url_object,
)
from .version import __version__

# ============================= CONSTANTS ===================================== #

# IP used for testing the connection to API
DUMMY_IP = "8.8.8.8"
ENDPOINTS = {
    "alerts": "v2/alert/search",
    "alert": "v2/alert/{alert_id}",
    "analyst_note": "v2/analystnote/publish",
    "update_alert": "/v2/alert/update",
}


class RecordedFutureManager:
    """RecordedFuture Manager."""

    def __init__(self, api_url, api_key, verify_ssl=False, siemplify=None):
        self.siemplify = siemplify
        self.api_url = api_url
        Config.init(
            client_verify_ssl=verify_ssl,
            rf_token=api_key,
            app_id=f"ps-google-soar/{__version__}",
        )
        self.analyst = AnalystNoteMgr()
        self.enrich = LookupMgr()
        self.collective_insights = CollectiveInsights()

        self.alerts = ClassicAlertMgr()
        self.playbook_alerts = PlaybookAlertMgr()

    def _ioc_reputation(
        self,
        entity,
        ioc_type,
        fields,
        include_links,
        collective_insights_enabled,
    ):
        if include_links:
            fields.append("links")

        try:
            data = self.enrich.lookup(entity, entity_type=ioc_type, fields=fields)
        except (ValidationError, EnrichmentLookupError) as e:
            raise RecordedFutureManagerError(f"Error enriching {entity}. Error {e}")

        if not data.is_enriched:
            raise RecordedFutureNotFoundError

        if collective_insights_enabled:
            try:
                creation_time = self.siemplify.case.creation_time
                case_timestamp = (
                    datetime.fromtimestamp(creation_time / 1000).isoformat()[:-3]
                    + 'Z'
                )
                insight = self.collective_insights.create(
                    ioc_value=entity,
                    ioc_type=ioc_type,
                    detection_type='playbook',
                    detection_name=self.siemplify.case.title,
                    timestamp=case_timestamp,
                    incident_id=str(self.siemplify.case.identifier),
                    incident_name=self.siemplify.case.title,
                    incident_type='google-secops-threat-detection',
                )
                self.collective_insights.submit(insight=insight, debug=False)
            except (ValidationError, CollectiveInsightsError) as err:
                self.siemplify.LOGGER.error(err)
        return data.content

    def get_ip_reputation(self, entity, include_links, collective_insights_enabled):
        """Get IP Reputation, works as a general function for all entity types
        :param entity: {str} The entity
        :param include_links {bool} False when links shouldn't be included
        :param collective_insights_enabled {bool} True when Collective Insights should be submitted
        :return: {dict} The related entities for given entity.
        """
        fields = ["intelCard", "location"]
        data = self._ioc_reputation(
            entity,
            "ip",
            fields,
            include_links,
            collective_insights_enabled,
        )
        return build_siemplify_ip_object(data, entity)

    def get_cve_reputation(self, entity, include_links, collective_insights_enabled):
        """Get CVE Reputation, works as a general function for all entity types
        :param entity: {str} The entity
        :param include_links {bool} False when links shouldn't be included
        :param collective_insights_enabled {bool} True when Collective Insights should be submitted
        :return: {dict} The related entities for given entity.
        """
        fields = ["intelCard"]
        data = self._ioc_reputation(
            entity,
            "vulnerability",
            fields,
            include_links,
            collective_insights_enabled,
        )
        return build_siemplify_cve_object(data, entity)

    def get_hash_reputation(self, entity, include_links, collective_insights_enabled):
        """Get Hash Reputation, works as a general function for all entity types
        :param entity: {str} The entity
        :param include_links {bool} False when links shouldn't be included
        :param collective_insights_enabled {bool} True when Collective Insights should be submitted
        :return: {dict} The related entities for given entity.
        """
        fields = ["intelCard", "hashAlgorithm"]
        data = self._ioc_reputation(
            entity,
            "hash",
            fields,
            include_links,
            collective_insights_enabled,
        )
        return build_siemplify_hash_object(data, entity)

    def get_host_reputation(self, entity, include_links, collective_insights_enabled):
        """Get Host Reputation, works as a general function for all entity types
        :param entity: {str} The entity
        :param include_links {bool} False when links shouldn't be included
        :param collective_insights_enabled {bool} True when Collective Insights should be submitted
        :return: {dict} The related entities for given entity.
        """
        fields = ["intelCard"]
        data = self._ioc_reputation(
            entity,
            "domain",
            fields,
            include_links,
            collective_insights_enabled,
        )
        return build_siemplify_host_object(data, entity)

    def get_url_reputation(self, entity, include_links, collective_insights_enabled):
        """Get URL Reputation, works as a general function for all entity types
        :param entity: {str} The entity
        :param include_links {bool} False when links shouldn't be included
        :param collective_insights_enabled {bool} True when Collective Insights should be submitted
        :return: {dict} The related entities for given entity.
        """
        fields = ["intelCard"]
        data = self._ioc_reputation(
            entity,
            "url",
            fields,
            include_links,
            collective_insights_enabled,
        )
        return build_siemplify_url_object(data, entity)

    def get_information_about_alert(self, alert_id):
        """Fetch information about specific Alert and return results to the case.
        :param alert_id: {str} The Alert ID
        :return: {AlertDetails} AlertDetails object.
        """
        try:
            response = self.alerts.fetch(alert_id)
        except (AlertFetchError, ValidationError) as err:
            raise RecordedFutureManagerError(
                f"Unable to lookup or parse {alert_id}. Error {err}",
            )
        return build_siemplify_alert_object(response)

    def get_alerts(
        self,
        existing_ids,
        start_timestamp,
        severity,
        extract_all_entities,
        limit=None,
        rules=None,
        fetch_statuses=CLASSIC_ALERT_DEFAULT_STATUSES,
    ):
        """Get security alerts from Recorded Future.
        :param existing_ids: {list} The list of existing ids.
        :param start_timestamp: {int} Timestamp for oldest detection to fetch.
        :param severity: {str} Severity to assign to alert.
        :param extract_all_entities: {bool} Whether to add all entities to Case.
        :param limit: {int} Number of Alerts to return.
        :param rules: {list} List of Alert Rules to fetch.
        :param fetch_statuses: {list} Statuses of Alerts to fetch.
        :return: {list} List of filtered Alert objects.
        """
        alerts = []
        time = self._build_triggered_filter(start_timestamp)
        alert_ids = []
        try:
            rule_ids = [
                rule.id_ for rule in self.alerts.fetch_rules(rules, max_results=1000)
            ]
            for status in fetch_statuses:
                alert_ids.extend(
                    alert.id_
                    for alert in self.alerts.search(
                        triggered=time,
                        rule_id=rule_ids,
                        status=status,
                        max_results=limit,
                        max_workers=10,
                    )
                )
            raw_alerts = self.alerts.fetch_bulk(ids=set(alert_ids), max_workers=10)
        except (AlertSearchError, AlertFetchError) as err:
            raise RecordedFutureManagerError(f"Unable to fetch alerts. Error {err}")

        for alert in raw_alerts:
            alert_id = alert.id_
            self.siemplify.LOGGER.info(f"processing alert {alert_id}")
            ai_insights = alert.ai_insights
            if not ai_insights:
                ai_insights_text = "AI Insights is not available for this alert."
            elif ai_insights.text:
                ai_insights_text = ai_insights.text
            else:
                ai_insights_text = ai_insights.comment

            try:
                alerts.append(
                    build_alert(
                        alert,
                        severity,
                        extract_all_entities,
                        ai_insights_text,
                    ),
                )
            except RecordedFutureDataModelTransformationLayerError as err:
                self.siemplify.LOGGER.error(
                    f"Error when transofrming alert {alert_id}. Skipping",
                )
                self.siemplify.LOGGER.error(err)

        filtered_alerts = filter_old_alerts(
            siemplify=self.siemplify,
            alerts=alerts,
            existing_ids=existing_ids,
            id_key=ALERT_ID_FIELD,
        )
        if isinstance(limit, int):
            return filtered_alerts[:limit]
        return filtered_alerts

    def _build_triggered_filter(self, start_timestamp):
        """Build triggered filter.
        :param start_timestamp: {int} Timestamp for oldest detection to fetch
        :return: {str} The triggered filter value.
        """
        return "[{}Z,]".format(
            datetime.fromtimestamp(start_timestamp / 1000).strftime(
                CONNECTOR_DATETIME_FORMAT,
            )[:-3],
        )

    def update_alert(self, alert_id, status, assignee, note):
        """Update Alert in Recorded Future
        :param alert_id: {str} The id of alert to update.
        :param status: {str} New status of the alert
        :param assignee: {str} Assignee to assign the alert to
        :param note: {str} Note to add to the alert
        :return: {dict} Response raw data.
        """
        if not alert_id:
            raise RecordedFutureManagerError("Alert id should be present")

        payload = {
            "id": alert_id,
        }

        if assignee is not None:
            payload["assignee"] = assignee
        if note is not None:
            payload["note"] = note
        if status is not None:
            payload["statusInPortal"] = status

        try:
            self.alerts.update([payload])
        except AlertUpdateError as err:
            raise RecordedFutureManagerError(f"Error updating alert {err}")
        return {"success": {"id": alert_id}}

    # ### ANALYST NOTES

    def get_analyst_notes(self, title, text, topic):
        """Get analyst notes
        :param title: {str} Note title
        :param text: {str} Note text
        :param topic: {str} Note topic
        :return: {dict} analyst_objects objects.
        """
        try:
            note = self.analyst.publish(title=title, text=text, topic=topic)
        except (ValidationError, AnalystNotePublishError) as err:
            raise RecordedFutureManagerError(
                f"Unable to publish note {title}. Error {err}",
            )
        return build_siemplify_analyst_note_object(note)

    # ### PLAYBOOK ALERTS

    def get_playbook_alerts(
        self,
        existing_ids,
        category,
        statuses,
        priority,
        severity,
        created_from=None,
        created_until=None,
        updated_from=None,
        updated_until=None,
        limit=PLAYBOOK_ALERT_API_LIMIT,
    ):
        """Fetches Playbook Alerts from Recorded Future matching the supplied parameters
        :param existing_ids: {list} The list of existing ids.
        :param category: {int} Playbook Alert categories to fetch.
        :param statuses: {int} Playbook Alert statuses to fetch.
        :param priority: {int} Playbook Alert priorities to fetch.
        :param severity: {str} Severity to assign to alert.
        :param created_from: {int} Filter by creation date. Defaults to None.
        :param created_until: {int} Filter by creation date. Defaults to None.
        :param updated_from: {int} Filter by update date. Defaults to None.
        :param updated_until: {int} Filter by update date. Defaults to None.
        :return: {list} List of filtered PlaybookAlert objects.
        """
        playbook_alerts = []
        try:
            raw_playbook_alerts = self.playbook_alerts.fetch_bulk(
                category=category,
                statuses=statuses,
                priority=priority,
                created_from=created_from,
                created_until=created_until,
                updated_from=updated_from,
                updated_until=updated_until,
                max_results=limit,
            )
        except (PlaybookAlertFetchError, ValidationError) as err:
            raise RecordedFutureManagerError(
                f"Unable to fetch playbook alerts. Error {err}",
            )

        for pba in raw_playbook_alerts:
            pba_id = pba.playbook_alert_id
            self.siemplify.LOGGER.info(f"Processing playbook alert {pba_id}")
            try:
                playbook_alerts.append(build_playbook_alert(pba, severity=severity))
            except RecordedFutureDataModelTransformationLayerError as err:
                msg = f"Error when transfrming playbook alert {pba_id}. Skipping"
                self.siemplify.LOGGER.error(msg)
                self.siemplify.LOGGER.error(err)

        filtered_alerts = filter_old_alerts(
            siemplify=self.siemplify,
            alerts=playbook_alerts,
            existing_ids=existing_ids,
            id_key=ALERT_ID_FIELD,
        )
        if isinstance(limit, int):
            return filtered_alerts[:limit]

        return filtered_alerts

    def add_lightweight_entity(self, entity, is_suspicious=False):
        """Adds a 'lightweight' RF entity to a case
        param entity: a string in format {ip|url|idn|hash}:<somevalue>
        param is_suspicious: whether the entity is suspicious.
        """
        if ":" not in entity:
            self.siemplify.warn(
                f"{entity} is not a lightweight entity. Skipping...",
            )
            return
        type_, entity = entity.split(":", 1)
        type_ = ENTITY_PREFIX_TYPE_MAP[type_]
        self.siemplify.add_entity_to_case(
            entity_identifier=entity,
            entity_type=type_,
            is_suspicous=is_suspicious,
            is_internal=False,
            is_enriched=False,
            is_vulnerable=True,
            properties={},
        )
        self.siemplify.LOGGER.info(f"Added entity {entity}")

    def refresh_domain_abuse(self, playbook_alert: PBA_DomainAbuse):
        """Adds case entities for Domain Abuse alert."""
        self.add_lightweight_entity(playbook_alert.panel_status.entity_id)

        for record in playbook_alert.panel_evidence_summary.resolved_record_list:
            suspicious = (record.risk_score or 0) > 24
            if record.entity is not None:
                self.add_lightweight_entity(record.entity, suspicious)
            else:
                self.siemplify.LOGGER.error(
                    f"Error trying to add entity {record!s} to case. Skipping",
                )

    def refresh_code_repo_leakage(self, playbook_alert):
        """Adds case entities for Code Repo Leakage alert."""
        suspicious = playbook_alert.panel_status.risk_score > 24
        self.add_lightweight_entity(
            playbook_alert.panel_status.entity_id,
            is_suspicious=suspicious,
        )
        for target in playbook_alert.panel_status.targets:
            entity = target.name
            if "." not in entity:
                self.siemplify.LOGGER.warn(
                    f"Entity {entity} is not a domain. Skipping...",
                )
                continue

            self.siemplify.add_entity_to_case(
                entity_identifier=entity,
                entity_type=EntityTypes.DOMAIN,
                is_suspicous=False,
                is_internal=False,
                is_enriched=False,
                is_vulnerable=True,
                properties={},
            )
            self.siemplify.LOGGER.info(f"Added entity {entity}")

    def refresh_cyber_vulnerability(self, playbook_alert):
        """Adds case entities for Cyber Vulnerability alert."""
        suspicious = playbook_alert.panel_status.risk_score > 24
        self.siemplify.add_entity_to_case(
            entity_identifier=playbook_alert.panel_status.entity_name,
            entity_type=EntityTypes.CVE,
            is_suspicous=suspicious,
            is_internal=False,
            is_enriched=False,
            is_vulnerable=True,
            properties={},
        )
        self.siemplify.LOGGER.info(
            f"Added entity {playbook_alert.panel_status.entity_name}",
        )

    def refresh_identity_novel_exposures(
        self,
        playbook_alert: PBA_IdentityNovelExposure,
    ):
        """Adds case entities for Identity Novel Exposure alert."""
        compromised_host = playbook_alert.panel_evidence_summary.compromised_host
        compromised_ip = playbook_alert.panel_evidence_summary.infrastructure.ip
        if entity_id := playbook_alert.panel_status.entity_id:
            self.add_lightweight_entity(entity_id)
        for target in playbook_alert.panel_status.targets:
            entity = target.name
            self.siemplify.add_entity_to_case(
                entity_identifier=entity,
                entity_type=EntityTypes.DOMAIN,
                is_suspicous=False,
                is_internal=False,
                is_enriched=False,
                is_vulnerable=True,
                properties={},
            )
            self.siemplify.LOGGER.info(f"Added entity {entity}")
        if compromised_ip:
            self.siemplify.add_entity_to_case(
                entity_identifier=compromised_ip,
                entity_type=EntityTypes.ADDRESS,
                is_suspicous=False,
                is_internal=True,
                is_enriched=False,
                is_vulnerable=True,
                properties={},
            )
            self.siemplify.LOGGER.info(f"Added entity {compromised_ip}")
        if compromised_host.computer_name:
            self.siemplify.add_entity_to_case(
                entity_identifier=compromised_host.computer_name,
                entity_type=EntityTypes.HOSTNAME,
                is_suspicous=False,
                is_internal=True,
                is_enriched=False,
                is_vulnerable=True,
                properties={},
            )
            self.siemplify.LOGGER.info(f"Added entity {compromised_host}")

    def refresh_pba_case(self, alert_id, category):
        """Fetches specified Playbook Alert from Recorded Future and adds entities.
        :param alert_id: {str} Playbook Alert ID.
        :param category: {int} Category of the Playbook Alert.
        :return: {dict} Playbook Alert Object.
        """
        func_map = {
            "domain_abuse": self.refresh_domain_abuse,
            "code_repo_leakage": self.refresh_code_repo_leakage,
            "cyber_vulnerability": self.refresh_cyber_vulnerability,
            "identity_novel_exposures": self.refresh_identity_novel_exposures,
        }
        self.siemplify.LOGGER.info(
            f"Fetching and refreshing Playbook Alert {alert_id}",
        )
        linked_cases = self.siemplify.get_cases_by_ticket_id(ticket_id=alert_id)
        try:
            playbook_alert = self.playbook_alerts.fetch(
                alert_id=alert_id,
                category=category,
            )
        except (ValidationError, PlaybookAlertFetchError) as err:
            raise RecordedFutureManagerError(
                f"Unable to refresh Playbook Alert. Error {err}",
            )

        if playbook_alert.category in func_map:
            func_map[playbook_alert.category](playbook_alert)
        return build_playbook_alert(playbook_alert, linked_cases)

    def get_pba_details(self, alert_id, category):
        """Fetches specified Playbook Alert from Recorded Future \
        :param alert_id: {str} Playbook Alert ID.
        :param category: {int} Category of the Playbook Alert.
        :return: {dict} Playbook Alert Object.
        """
        self.siemplify.LOGGER.info(f"Fetching Playbook Alert {alert_id}")
        try:
            playbook_alert = self.playbook_alerts.fetch(
                alert_id=alert_id,
                category=category,
            )
        except (ValidationError, PlaybookAlertFetchError) as err:
            raise RecordedFutureManagerError(
                f"Unable to fetch Playbook Alert. Error {err}",
            )

        return build_playbook_alert(playbook_alert)

    def update_playbook_alert(
        self,
        alert_id,
        category=None,
        status=None,
        assignee=None,
        log_entry=None,
        priority=None,
        reopen_strategy=None,
    ):
        """Update Alert in Recorded Future.

        :param alert_id: {str} The id of alert to update.
        :param category: {str} The category of alert to update.
        :param status: {str} New status of the alert
        :param assignee: {str} Assignee to assign the alert to
        :param log_entry: {str} Log comment to add to the update
        :param priority: {str} Priority to assign the alert to
        :param reopen_strategy: {str} Strategy for reopening an alert
        :return: {dict} Response raw data.
        """
        try:
            alert = self.playbook_alerts.fetch(alert_id, category)
            self.playbook_alerts.update(
                alert=alert,
                priority=priority,
                status=status,
                assignee=assignee,
                log_entry=log_entry,
                reopen_strategy=reopen_strategy,
            )
        except (
            ValidationError,
            PlaybookAlertFetchError,
            PlaybookAlertUpdateError,
        ) as err:
            raise RecordedFutureManagerError(f"Error updating playbook alert {err}")
        return {"success": {"id": alert_id}}

    def test_connectivity(self):
        """Test integration connectivity using ip:8.8.8.8
        :return: {bool} is succeed.
        """
        try:
            self.get_ip_reputation(DUMMY_IP, False, collective_insights_enabled=False)
        except RecordedFutureManagerError:
            return False
