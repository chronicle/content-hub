from __future__ import annotations
import requests
import json
from copy import deepcopy
from .BlueLivExceptions import BlueLivException
from .BlueLivParser import BlueLivParser
from .UtilsManager import filter_old_alerts
from .consts import (
    AUTH_QUERY,
    ADD_COMMENT_TO_THREAT_URL,
    MARK_THREAT_AS_FAVORITE_URL,
    FAVORITE_STATUS,
    PING_URL,
    GET_LABELS_URL,
    GET_THREAT_URL,
    ADD_LABELS_TO_THREATS_URL,
    GET_THREATS_BY_FILTERS_URL,
    ORDER_BY_STRING,
    MAX_RESULTS_LIMIT,
    GET_THREAT_EXTRADATA_URL,
    HACKTIVISM,
    DATA_LEAKAGE,
    CREDENTIALS,
    DARK_WEB,
    DOMAIN_PROTECTION,
    MALWARE,
    MEDIA_TRACKER,
    MOBILE_APPS,
    SOCIAL_MEDIA,
    CUSTOM_MODULE,
    CREDIT_CARD,
    REMOVE_LABELS_TO_THREATS_URL,
    ENRICH_IP_URL,
    ENRICH_HASH_URL,
    ENRICH_URL_URL,
    ENRICH_ACTOR_URL,
    ENRICH_SIGNATURE_URL,
    ENRICH_CAMPAIGN_URL,
    ENRICH_CVE_URL,
    GET_THREAT_ACTOR_DETAILS_URL,
    GET_THREAT_SIGNATURE_DETAILS_URL,
    GET_THREAT_CAMPAIGN_DETAILS_URL,
    GET_BLUELIV_DETAILS_URL,
    CUSTOM_LINK_URL,
    GET_URL_DETAILS_URL,
    GET_ENTITY_DETAILS,
)

HEADERS = {"Content-Type": "application/json;", "Accept": "application/json"}


class BlueLivManager:
    def __init__(
        self,
        api_root=None,
        username=None,
        password=None,
        organization_id=None,
        verify_ssl=False,
        siemplify_logger=None,
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: API Root of the BlueLiv
        :param username: username of the BlueLiv
        :param password: Password for the given username
        :param organization_id: Organization ID of the BlueLiv
        :param verify_ssl: If enabled, verify the SSL certificate for the connection to the BlueLiv server is valid.
        :param siemplify_logger: Siemplify logger.
        """

        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.username = username
        self.password = password
        self.organization_id = organization_id
        self.siemplify_logger = siemplify_logger
        self.parser = BlueLivParser()

        self.session = requests.session()
        self.session.headers = deepcopy(HEADERS)
        self.session.verify = verify_ssl
        self.access_token, self.jsession_id, self.jsession_id_version = (
            self.generate_token()
        )
        self.session.headers.update({"x-cookie": f"{self.access_token}"})
        self.module_id = None

    def module_id_setter(self, module_id):
        """
        Function that sets the module_id variable
        """
        self.module_id = module_id

    def generate_token(self):
        """
        Function to generate API Token
        :return {str}: API Token
        """
        payload = {"username": self.username, "password": self.password}

        res = self.session.post(AUTH_QUERY.format(self.api_root), json=payload)
        self.validate_response(res)
        return (
            res.json().get("token"),
            res.cookies.get("JSESSIONID"),
            res.cookies.get("JSESSIONIDVERSION"),
        )

    def test_connectivity(self):
        """
        Function to test the connectivity to BlueLiv
        """
        res = self.session.get(PING_URL.format(self.api_root, self.organization_id))
        self.validate_response(res)

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            try:
                response.json()
            except:
                # Not a JSON - return content
                raise BlueLivException(
                    f"{error_msg}: {error} - {error.response.content}"
                )

            raise BlueLivException(
                f"{error_msg}: {response.json().get('name')} {json.dumps(response.json())}"
            )

    def add_comment_to_threat(self, module_id, module_type, threat_id, comment):
        """
        Function to add comment to a threat
        :param {str}: module_id Module ID to use
        :param {str}: module_type Module Type to use
        :param {str}: threat_id Threat ID to use
        :param {str}: comment Comment to the Threat
        :return {str}: Comment Object
        """

        url = ADD_COMMENT_TO_THREAT_URL.format(
            self.api_root, self.organization_id, module_id, module_type, threat_id
        )

        payload = {"comment": comment}

        res = self.session.put(url, json=payload)
        self.validate_response(res)

        return [
            self.parser.build_siemplify_comment_object(comment)
            for comment in res.json()
        ]

    def mark_threat_as_favorite(self, module_id, module_type, threat_id, status):
        """
        Function to mark threat as favorite
        :param {str}: module_id Module ID to use
        :param {str}: module_type Module Type to use
        :param {str}: threat_id Threat ID to use
        :param {str}: status New Status Of the Trheat
        """

        status = FAVORITE_STATUS.get(status)

        url = MARK_THREAT_AS_FAVORITE_URL.format(
            self.api_root, self.organization_id, module_id, module_type
        )

        payload = {"status": status, "resource": threat_id}

        res = self.session.put(url, json=payload)
        self.validate_response(res)

    def get_labels(self):
        """
        Function to get all the labels from BlueLiv
        return: {List} List of Label Ojects
        """
        url = GET_LABELS_URL.format(self.api_root, self.organization_id)

        res = self.session.get(url)
        self.validate_response(res)

        return self.parser.build_siemplify_label_object(res.json())

    def check_if_threat_exist(self, module_id, module_type, threat_id):
        """
        Function that checks if threat with threat ID exist in BlueLiv
        :param module_id {str}: Module ID to use
        :param module_type {str}: Module Type to use
        :param threat_id {str}: Threat ID to use
        """
        url = GET_THREAT_URL.format(
            self.api_root, self.organization_id, module_id, module_type, threat_id
        )

        res = self.session.get(url)
        self.validate_response(res)

    def add_label_to_threat(self, label, module_id, module_type, threat_id):
        """
        Function that add a label to a list of threats in BlueLiv
        :param module_id {str}: Module ID to use
        :param module_type {str}: Module Type to use
        :param threat_id {str}: The threat ID to use
        """
        url = ADD_LABELS_TO_THREATS_URL.format(
            self.api_root, self.organization_id, module_id, module_type
        )

        payload = {"label": label, "resources": [threat_id]}

        res = self.session.put(url, json=payload)
        self.validate_response(res)

    def remove_label_to_threat(self, label, module_id, module_type, threat_id):
        """
        Function that removes a label to a list of threats in BlueLiv
        :param module_id {str}: Module ID to use
        :param module_type {str}: Module Type to use
        :param threat_id {str}: The threat ID to use
        """
        url = REMOVE_LABELS_TO_THREATS_URL.format(
            self.api_root, self.organization_id, module_id, module_type
        )

        payload = {"label": label, "resources": [threat_id]}

        res = self.session.put(url, json=payload)
        self.validate_response(res)

    def enrich_ip_address(self, entity_id):
        """
        Function that gets details for IP Address and it's used for enrichment
        :param entity_id {str}: Entity Identifier
        return: {IP_Object} IP object containting details about the IP Address
        """
        url = ENRICH_IP_URL.format(self.api_root, entity_id)

        link = CUSTOM_LINK_URL.format(
            self.api_root,
            self.organization_id,
            self.module_id,
            "indicators/ip/resource",
        )

        response = self.session.get(url)
        self.validate_response(response)

        return self.parser.build_siemplify_ip_object(data=response.json(), link=link)

    def enrich_hash(self, entity_id):
        """
        Function that gets details for Hash and it's used for enrichment
        :param entity_id {str}: Entity Identifier
        return: {Hash_Object} Hash object containting details about the Hash
        """
        url = ENRICH_HASH_URL.format(self.api_root, entity_id)
        link = CUSTOM_LINK_URL.format(
            self.api_root,
            self.organization_id,
            self.module_id,
            "indicators/malware/resource",
        )

        response = self.session.get(url)
        self.validate_response(response)

        return self.parser.build_siemplify_hash_object(data=response.json(), link=link)

    def get_entity_data(self, entity_id, module_filter, label_filter):
        """
        Function that gets details for an entity
        :param module_filter {str} Module Filter
        :param label_filter {str} Label Filter
        :param entity_id {str}: Entity Identifier
        return: {EntityObject} Entity object containting details about the entity
        """

        url = GET_ENTITY_DETAILS.format(self.api_root, self.organization_id, entity_id)

        response = self.session.get(url)
        self.validate_response(response)

        return self.parser.build_siemplify_entity_object(
            data=response.json(), module_filter=module_filter, label_filter=label_filter
        )

    def enrich_url(self, entity_id):
        """
        Function that gets details for URL and it's used for enrichment
        :param entity_id {str}: Entity Identifier
        return: {URL_Object} URL object containting details about the URL
        """
        url = ENRICH_URL_URL.format(self.api_root, entity_id)
        link = CUSTOM_LINK_URL.format(
            self.api_root,
            self.organization_id,
            self.module_id,
            "indicators/crime-server/resource",
        )

        response = self.session.get(url)
        self.validate_response(response)

        return self.parser.build_siemplify_url_object(data=response.json(), link=link)

    def enrich_cve(self, entity_id):
        """
        Function that gets details for CVE and it's used for enrichment
        :param entity_id {str}: Entity Identifier
        return: {CVE_Object} CVE object containting details about the CVE
        """
        url = ENRICH_CVE_URL.format(self.api_root, entity_id)
        link = CUSTOM_LINK_URL.format(
            self.api_root, self.organization_id, self.module_id, "cves"
        )

        response = self.session.get(url)
        self.validate_response(response)

        return self.parser.build_siemplify_cve_object(data=response.json(), link=link)

    def enrich_threatactor(self, entity_id):
        """
        Function that gets details for ThreatActor and it's used for enrichment
        :param entity_id {str}: Entity Identifier
        return: {ThreatActor_Object} ThreatActor object containting details about the ThreatActor
        """
        url = ENRICH_ACTOR_URL.format(self.api_root, entity_id)
        link = CUSTOM_LINK_URL.format(
            self.api_root, self.organization_id, self.module_id, "actors"
        )

        response = self.session.get(url)
        self.validate_response(response)

        return self.parser.build_siemplify_threat_actor_object(
            data=response.json(), link=link
        )

    def enrich_threatsignature(self, entity_id):
        """
        Function that gets details for ThreatSignature and it's used for enrichment
        :param entity_id {str}: Entity Identifier
        return: {ThreatSignature_Object} ThreatSignature object containting details about the ThreatSignature
        """
        url = ENRICH_SIGNATURE_URL.format(self.api_root, entity_id)
        link = CUSTOM_LINK_URL.format(
            self.api_root, self.organization_id, self.module_id, "signatures"
        )

        response = self.session.get(url)
        self.validate_response(response)

        return self.parser.build_siemplify_threat_signature_object(
            data=response.json(), link=link
        )

    def enrich_threatcampaign(self, entity_id):
        """
        Function that gets details for ThreatCampaign and it's used for enrichment
        :param entity_id {str}: Entity Identifier
        return: {ThreatCampaign_Object} ThreatCampaign object containting details about the ThreatCampaign
        """
        url = ENRICH_CAMPAIGN_URL.format(self.api_root, entity_id)
        link = CUSTOM_LINK_URL.format(
            self.api_root, self.organization_id, self.module_id, "campaigns"
        )

        response = self.session.get(url)
        self.validate_response(response)

        return self.parser.build_siemplify_threat_campaign_object(
            data=response.json(), link=link
        )

    def get_crime_server_details(self, entity_id):
        """
        Function to fetch the CrimeServer ID
        :param entity_id {str}: Entity Identifier
        return: {Threat_Object} Threat object containting details about the Threat
        """
        params = {"dork": f'value:"{entity_id}"'}
        url = GET_URL_DETAILS_URL.format(self.api_root, entity_id)

        response = self.session.get(url, params=params)
        self.validate_response(response)

        return self.parser.build_siemplify_threat_object_details_object(
            data=response.json()
        )

    def get_threat_actor_details(self, entity_id):
        """
        Function to fetch the ThreatActor ID
        :param entity_id {str}: Entity Identifier
        return: {Threat_Object} Threat object containting details about the Threat
        """
        params = {"dork": f'name:"{entity_id}"'}
        url = GET_THREAT_ACTOR_DETAILS_URL.format(self.api_root, entity_id)

        response = self.session.get(url, params=params)
        self.validate_response(response)

        return self.parser.build_siemplify_threat_object_details_object(
            data=response.json()
        )

    def get_threat_signature_details(self, entity_id):
        """
        Function to fetch the ThreatSignature ID
        :param entity_id {str}: Entity Identifier
        return: {Threat_Object} Threat object containting details about the Threat
        """
        params = {"dork": f'name:"{entity_id}"'}
        url = GET_THREAT_SIGNATURE_DETAILS_URL.format(self.api_root, entity_id)

        response = self.session.get(url, params=params)
        self.validate_response(response)

        return self.parser.build_siemplify_threat_object_details_object(
            data=response.json()
        )

    def get_blueliv_context_information(self, module_id=None, module_type=None):
        """
        Function that gets the module id from Blueliv
        :param module_id {str}: Module ID
        :param module_type {str}: Module Type
        return: {Threat_Context_Object} ThreatContext object containting module id
        """
        url = GET_BLUELIV_DETAILS_URL.format(self.api_root, self.organization_id)

        response = self.session.get(url)
        self.validate_response(response)

        return self.parser.get_threat_context_id(
            data=response.json(), module_id=module_id, module_type=module_type
        )

    def get_threat_campaign_details(self, entity_id):
        """
        Function to fetch the ThreatCampaign ID
        :param entity_id {str}: Entity Identifier
        return: {Threat_Object} Threat object containting details about the Threat
        """
        params = {"dork": f'name:"{entity_id}"'}
        url = GET_THREAT_CAMPAIGN_DETAILS_URL.format(self.api_root, entity_id)

        response = self.session.get(url, params=params)
        self.validate_response(response)

        return self.parser.build_siemplify_threat_object_details_object(
            data=response.json()
        )

    def get_threats(
        self,
        existing_ids,
        limit,
        timestamp,
        analysis_type,
        labels,
        read_status,
        only_starred,
        only_related_to_incidents,
    ):
        """
        Get threats with filter
        :param existing_ids: {list} The list of existing ids.
        :param limit: {int} Number of threats to fetch.
        :param timestamp: {int} The timestamp from where to fetch threats.
        :param analysis_type: {str} Analysis type to filter by.
        :param labels: {list} List of label ids to filter by.
        :param read_status: {int} Reading status to filter by.
        :param only_starred: {bool} If true, will fetch only starred threats.
        :param only_related_to_incidents: {bool} If true, will fetch only threats related to incidents.
        :return: {list} List of Threat objects.
        """
        url = GET_THREATS_BY_FILTERS_URL.format(self.api_root, self.organization_id, 0)
        params = {
            "since": timestamp,
            "analysisCalcResult": analysis_type,
            "read": read_status,
            "starred": only_starred,
            "o": ORDER_BY_STRING,
            "maxRows": MAX_RESULTS_LIMIT,
        }

        if labels:
            params["labels"] = labels

        if only_related_to_incidents is not None:
            params["incidents"] = only_related_to_incidents

        response = self.session.get(url, params=params)
        self.validate_response(response)
        threats = self.parser.build_all_threats(raw_json=response.json())
        detailed_threats = []
        for threat in threats:
            if threat.module_type != MALWARE:
                detailed_threats.append(
                    self.get_threat_with_details(
                        threat_id=threat.id,
                        module_id=threat.module_id,
                        module_type=threat.module_type,
                    )
                )
            else:
                detailed_threats.append(threat)

        filtered_threats = filter_old_alerts(
            logger=self.siemplify_logger,
            alerts=detailed_threats,
            existing_ids=existing_ids,
        )
        return sorted(filtered_threats, key=lambda item: item.changed_at)[:limit]

    def get_threat_with_details(self, threat_id, module_id, module_type):
        """
        Get threat details with id.
        :param threat_id: {int} Id of the threat.
        :param module_id: {int} Id of the module.
        :param module_type: {str} Type of the module.
        :return: {Threat} object
        """
        url = GET_THREAT_URL.format(
            self.api_root,
            self.organization_id,
            module_id,
            module_type.lower(),
            threat_id,
        )
        res = self.session.get(url)
        self.validate_response(res)
        if module_type != MALWARE:
            return self.parser.build_siemplify_threat_object(threat_data=res.json())
        return self.parser.build_siemplify_malware_object(malware_data=res.json())

    def get_threat_extradata_info(self, threat_id, module_id, module_type):
        """
        Get threat details with id.
        :param threat_id: {int} Id of the threat.
        :param module_id: {int} Id of the module.
        :param module_type: {str} Type of the module.
        :return: {ExtraData} object
        """
        url = GET_THREAT_EXTRADATA_URL.format(
            self.api_root,
            self.organization_id,
            module_id,
            module_type.lower(),
            threat_id,
        )
        res = self.session.get(url)
        self.validate_response(res)
        if res.json():
            return self.parser.build_siemplify_extradata_object(
                raw_json=res.json(), module_type=module_type
            )

    def create_events_by_module_type(self, threat):
        """
        Create events for Siemplify Alert by module type of the threat
        :param threat: {Threat} object
        :return: {list} List of events
        """
        events = [threat.to_main_event()]
        if threat.module_type in [
            HACKTIVISM,
            DATA_LEAKAGE,
            DARK_WEB,
            DOMAIN_PROTECTION,
            MEDIA_TRACKER,
            MOBILE_APPS,
            SOCIAL_MEDIA,
            CUSTOM_MODULE,
        ]:
            extra_data = self.get_threat_extradata_info(
                threat_id=threat.id,
                module_id=threat.module_id,
                module_type=threat.module_type,
            )
            if extra_data:
                events.append(extra_data.to_event())
        elif threat.module_type == CREDENTIALS:
            for credential in threat.to_json().get("credentials", []):
                credential["event_type"] = f"{CREDENTIALS} related Credential"
                events.append(credential)
        elif threat.module_type == MALWARE:
            detailed_malware = self.get_threat_with_details(
                threat_id=threat.id,
                module_id=threat.module_id,
                module_type=threat.module_type,
            )
            if detailed_malware:
                events.append(detailed_malware.to_event())
                for host in detailed_malware.hosts:
                    host["event_type"] = f"{MALWARE} related Host"
                    events.append(host)
        elif threat.module_type.lower().startswith(CREDIT_CARD):
            for credit_card in threat.to_json().get("credit_cards", []):
                credit_card["event_type"] = f"{threat.module_type} related Credit Card"
                events.append(credit_card)

        return events
