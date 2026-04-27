# ============================================================================#
# title           :RecordedFutureManager.py
# description     :This Module contain all FutureRecords operations functionality
# author          :severins@siemplify.co
# date            :03-10-2019
# python_version  :3.7
# libraries       : requests, urllib
# requirements    :
# product_version :??
# ============================================================================#

# ============================= IMPORTS ===================================== #

from __future__ import annotations
import requests
from urllib.parse import quote_plus, urlparse, urljoin, quote
from .RecordedFutureDataModelTransformationLayer import (
    build_siemplify_ip_object,
    build_siemplify_cve_object,
    build_siemplify_hash_object,
    build_siemplify_host_object,
    build_siemplify_url_object,
    build_siemplify_related_entities_object,
    build_alerts,
    get_alert,
    build_siemplify_ioc_objects,
    build_siemplify_alert_object,
    build_siemplify_analyst_note_object,
)
from .UtilsManager import validate_response, check_errors_in_response
from .constants import CONNECTOR_DATETIME_FORMAT, DEFAULT_LIMIT, ALERT_ID_FIELD
import datetime
from soar_sdk.SiemplifyDataModel import EntityTypes
import json
from TIPCommon import filter_old_alerts

# ============================= CONSTANTS ===================================== #

LIST_OF_AVAILABLE_API_PARAMS = ["domain", "hash", "ip", "url", "vulnerability"]
# IP used for testing the connection to API
DUMMY_IP = "8.8.8.8"
GET_REPUTATION_API_FIELDS = "intelCard,location,risk,timestamps,hashAlgorithm"
GET_RELATED_ENTITIES_API_FIELDS = "relatedEntities,intelCard"

ENDPOINTS = {
    "alerts": "v2/alert/search",
    "alert": "v2/alert/{alert_id}",
    "analyst_note": "v2/analystnote/publish",
    "update_alert": "/v2/alert/update",
}


class RecordedFutureManager:
    """
    RecordedFuture Manager
    """

    def __init__(self, api_url, api_key, verify_ssl=False, siemplify=None):
        self.api_url = api_url
        self.api_key = api_key
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.siemplify = siemplify

        headers = {"X-RFToken": self.api_key, "Content-Type": "application/json"}

        self.session.headers.update(headers)

    def get_ip_reputation(self, entity, include_related_entities):
        """
        Get IP Reputation, works as a general function for all entity types
        :param entity: {str} The entity
        :param include_related_entities {bool} False when the related entities shouldn't be included in enrichment
        :return: {dict} The related entities for given entity
        """
        fields_payload = GET_REPUTATION_API_FIELDS

        if include_related_entities:
            fields_payload = f"{fields_payload}, {GET_RELATED_ENTITIES_API_FIELDS}"

        entity = quote_plus(entity)
        response = self.session.get(
            url=f"{self.api_url}/v2/ip/{entity}", params={"fields": fields_payload}
        )

        validate_response(response)
        return build_siemplify_ip_object(response, entity)

    def get_cve_reputation(self, entity, include_related_entities):
        """
        Get CVE Reputation, works as a general function for all entity types
        :param entity: {str} The entity
        :param include_related_entities {bool} False when the related entities shouldn't be included in enrichment
        :return: {dict} The related entities for given entity
        """
        fields_payload = GET_REPUTATION_API_FIELDS

        if include_related_entities:
            fields_payload = f"{fields_payload}, {GET_RELATED_ENTITIES_API_FIELDS}"

        entity = quote_plus(entity)
        response = self.session.get(
            url=f"{self.api_url}/v2/vulnerability/{entity}",
            params={"fields": fields_payload},
        )
        validate_response(response)

        return build_siemplify_cve_object(response, entity)

    def get_hash_reputation(self, entity, include_related_entities):
        """
        Get Hash Reputation, works as a general function for all entity types
        :param entity: {str} The entity
        :param include_related_entities {bool} False when the related entities shouldn't be included in enrichment
        :return: {dict} The related entities for given entity
        """
        fields_payload = GET_REPUTATION_API_FIELDS
        if include_related_entities:
            fields_payload = f"{fields_payload}, {GET_RELATED_ENTITIES_API_FIELDS}"

        entity = quote_plus(entity)
        response = self.session.get(
            url=f"{self.api_url}/v2/hash/{entity}", params={"fields": fields_payload}
        )

        validate_response(response)
        return build_siemplify_hash_object(response, entity)

    def get_host_reputation(self, entity, include_related_entities):
        """
        Get Host Reputation, works as a general function for all entity types
        :param entity: {str} The entity
        :param include_related_entities {bool} False when the related entities shouldn't be included in enrichment
        :return: {dict} The related entities for given entity
        """
        fields_payload = GET_REPUTATION_API_FIELDS

        if include_related_entities:
            fields_payload = f"{fields_payload}, {GET_RELATED_ENTITIES_API_FIELDS}"

        entity = quote_plus(entity)
        response = self.session.get(
            url=f"{self.api_url}/v2/domain/{entity}", params={"fields": fields_payload}
        )

        validate_response(response)
        return build_siemplify_host_object(response, entity)

    def get_url_reputation(self, entity, include_related_entities):
        """
        Get URL Reputation, works as a general function for all entity types
        :param entity: {str} The entity
        :param include_related_entities {bool} False when the related entities shouldn't be included in enrichment
        :return: {dict} The related entities for given entity
        """
        fields_payload = GET_REPUTATION_API_FIELDS

        if include_related_entities:
            fields_payload = f"{fields_payload}, {GET_RELATED_ENTITIES_API_FIELDS}"

        entity = quote_plus(entity)
        response = self.session.get(
            url=f"{self.api_url}/v2/url/{entity}", params={"fields": fields_payload}
        )

        validate_response(response)
        return build_siemplify_url_object(response, entity)

    def get_cve_related_entities(self, entity):
        """
        Get CVE Related Entities, works as a general function for all entities
        :param entity: {str} The entity
        :return: {dict} The related entities for given entity
        """
        entity = quote(entity, safe="")
        response = self.session.get(
            url=f"{self.api_url}/v2/vulnerability/{entity}",
            params={"fields": GET_RELATED_ENTITIES_API_FIELDS},
        )

        validate_response(response)
        return build_siemplify_related_entities_object(response, entity)

    def get_hash_related_entities(self, entity):
        """
        Get Hash Related Entities, works as a general function for all entities
        :param entity: {str} The entity
        :return: {dict} The related entities for given entity
        """
        entity = quote(entity, safe="")
        response = self.session.get(
            url=f"{self.api_url}/v2/hash/{entity}",
            params={"fields": GET_RELATED_ENTITIES_API_FIELDS},
        )

        validate_response(response)
        return build_siemplify_related_entities_object(response, entity)

    def get_ip_related_entities(self, entity):
        """
        Get IP Related Entities, works as a general function for all entities
        :param entity: {str} The entity
        :return: {dict} The related entities for given entity
        """
        entity = quote(entity, safe="")
        response = self.session.get(
            url=f"{self.api_url}/v2/ip/{entity}",
            params={"fields": GET_RELATED_ENTITIES_API_FIELDS},
        )

        validate_response(response)
        return build_siemplify_related_entities_object(response, entity)

    def get_host_related_entities(self, entity):
        """
        Get Host Related Entities, works as a general function for all entities
        :param entity: {str} The entity
        :return: {dict} The related entities for given entity
        """
        entity = quote(entity, safe="")
        response = self.session.get(
            url=f"{self.api_url}/v2/domain/{entity}",
            params={"fields": GET_RELATED_ENTITIES_API_FIELDS},
        )

        validate_response(response)
        return build_siemplify_related_entities_object(response, entity)

    def build_ioc_related_entity_payload(self, entities):
        """
        Function that prepares the IOC related entities payload
        :param entities: {list} list of entities to process
        :return: {dict} Payload used for IOC query
        """
        payload = {"ip": [], "url": [], "vulnerability": [], "hash": [], "domain": []}

        for entity in entities:

            if entity.entity_type == EntityTypes.ADDRESS:
                addresses = payload.get("ip")
                addresses.append(entity.identifier)
            if entity.entity_type == EntityTypes.URL:
                # For URL entities we need to check the structure, if the URL is in form of: example.com, then it should be processed as domain
                split_url = urlparse(entity.identifier)
                if (
                    split_url.scheme == ""
                    and split_url.query == ""
                    and len(split_url.path.rsplit("/", 1)) == 1
                ):
                    hostnames = payload.get("domain")
                    hostnames.append(entity.identifier)
                else:
                    urls = payload.get("url")
                    urls.append(entity.identifier)
            if entity.entity_type == EntityTypes.CVE:
                cves = payload.get("vulnerability")
                cves.append(entity.identifier)
            if entity.entity_type == EntityTypes.FILEHASH:
                hashes = payload.get("hash")
                hashes.append(entity.identifier)
            if entity.entity_type == EntityTypes.HOSTNAME:
                hostnames = payload.get("domain")
                hostnames.append(entity.identifier)

        return payload

    def get_ioc_related_entity_objects(self, entities):
        """
        Fetch information about multiple entities, with different types
        :param entities: {list} The list of entities
        :return: {dict} CommonData objects
        """
        payload = self.build_ioc_related_entity_payload(entities=entities)

        response = self.session.post(
            url=f"{self.api_url}/v2/soar/enrichment?metadata=false", json=payload
        )

        validate_response(response)
        return build_siemplify_ioc_objects(response.json())

    def get_information_about_alert(self, alert_id):
        """
        Fetch information about specific Alert and return results to the case.
        :param alert_id: {str} The Alert ID
        :return: {AlertDetails} AlertDetails object
        """
        response = self.session.get(url=f"{self.api_url}/v2/alert/{alert_id}")

        validate_response(response)
        return build_siemplify_alert_object(response.json())

    def test_connectivity(self):
        """
        Test integration connectivity using ip:8.8.8.8
        :return: {bool} is succeed
        """
        try:
            self.get_ip_reputation(DUMMY_IP, False)
        except requests.HTTPError:
            return False

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_url, ENDPOINTS[url_id].format(**kwargs))

    def get_alerts(
        self, existing_ids, limit, start_timestamp, severity, get_alerts_details
    ):
        """
        Get security alerts from Recorded Future.
        :param existing_ids: {list} The list of existing ids.
        :param start_timestamp: {int} Timestamp for oldest detection to fetch.
        :param limit: {int} The limit for results.
        :param severity: {str} Severity to assign to alert.
        :param get_alerts_details: {bool} Weather get alert full details or no.
        :return: {list} List of filtered Alert objects.
        """
        url = self._get_full_url("alerts")

        params = {
            "triggered": self._build_triggered_filter(start_timestamp),
            "limit": max(limit, DEFAULT_LIMIT),
            "orderby": "triggered",
            "direction": "asc",
        }

        response = self.session.get(url=url, params=params)
        validate_response(response)
        alerts = build_alerts(response.json(), severity)

        if get_alerts_details:
            alerts = [
                get_alert(self.get_alert_full_details(alert.id), severity)
                for alert in alerts
            ]

        filtered_alerts = filter_old_alerts(
            siemplify=self.siemplify,
            alerts=alerts,
            existing_ids=existing_ids,
            id_key=ALERT_ID_FIELD,
        )

        return filtered_alerts

    def get_alert_full_details(self, alert_id):
        """
        Get alert full details.
        :param alert_id: {str} The id of alert to get full details.
        :return: {dict} Response raw data.
        """
        url = self._get_full_url("alert", alert_id=alert_id)
        response = self.session.get(url=url)
        validate_response(response)
        return response.json()

    def _build_triggered_filter(self, start_timestamp):
        """
        Build triggered filter.
        :param start_timestamp: {int} Timestamp for oldest detection to fetch
        :return: {str} The triggered filter value
        """
        return f"[{datetime.datetime.fromtimestamp(start_timestamp / 1000) .strftime(CONNECTOR_DATETIME_FORMAT)[:-3]}Z,]"

    def get_analyst_notes(self, ids, title, text, topic, source):
        """
        Get analyst notes
        :param ids: {list} Recorded future ids list
        :param title: {str} Note title
        :param text: {str} Note text
        :param topic: {str} Note topic
        :param source: {str} Note source
        :return: {dict} analyst_objects objects
        """
        params = {"source": source, "resolveEntities": False}
        payload = {"title": title, "text": text, "note_entities": ids}

        if topic:
            payload["topic"] = topic

        response = self.session.post(
            url=self._get_full_url("analyst_note"),
            params=params,
            data=json.dumps(payload),
        )
        validate_response(response)

        return build_siemplify_analyst_note_object(response.json())

    def update_alert(self, alert_id, status, assignee, note):
        """
        Update Alert in Recorded Future
        :param alert_id: {str} The id of alert to update.
        :param status: {str} New status of the alert
        :param assignee: {str} Assignee to assign the alert to
        :param note: {str} Note to add to the alert
        :return: {dict} Response raw data.
        """
        url = self._get_full_url("update_alert")

        payload = {"id": alert_id}

        if assignee is not None:
            payload["assignee"] = assignee
        if note is not None:
            payload["note"] = note
        if status is not None:
            payload["status"] = status

        payload = json.dumps(payload)
        payload = f"[{payload}]"

        response = self.session.post(url=url, data=payload)
        validate_response(response)
        check_errors_in_response(response)
        return response.json().get("success")
