# ============================== IMPORTS ==================================== #
from __future__ import annotations
from .datamodels import *

# ============================== CONSTS ==================================== #

RESULT_LINK = "https://portal-digitalshadows.com/search?q={}"
VULNERABILITY = "Vulnerability"
EXPLOIT = "Exploit"


# ============================== CLASSES ==================================== #
class DigitalShadowsParser:

    def __init__(self, entityTypes):
        """
        :param entityTypes: The types of entities defiled in DigitalShadowsManager class
                            Added hera via dependency injection to prevent cross import
        """
        self.entityTypes = entityTypes

    def build_hash_object(self, hash_data_entities, file_hash):
        """
        Builds Hash data object
        :param hash_data_entities: the list of hash entities
        :param file_hash: The file hash for creating the link
        :return: The Hash object or None
        """
        cylance_entity = None
        webroot_entity = None

        for hash_data in hash_data_entities:
            enitity_type = hash_data.get("type")
            if (
                cylance_entity is None
                and enitity_type == self.entityTypes.CYLANCE_FILE_HASH
            ):
                cylance_entity = hash_data

            if (
                webroot_entity is None
                and enitity_type == self.entityTypes.WEBROOT_FILE_HASH
            ):
                webroot_entity = hash_data

            if cylance_entity and webroot_entity:
                break
        if not cylance_entity and not webroot_entity:
            return None

        cylance_file_hash_generalScore = None
        cylance_file_hash_classifiers_ml = None
        cylance_file_hash_classifiers_human = None
        cylance_file_hash_classifiers_industry = None
        webroot_file_hash_category = None
        webroot_file_hash_malwareCategory = None
        webroot_file_hash_fileSizeBytes = None
        webroot_file_hash_fileLastSeen = None
        webroot_file_hash_sourceUrls = None

        raw_data = {"content": hash_data_entities}
        if cylance_entity:
            file_hash_info = cylance_entity.get("entity", {}).get("fileHashInfo")
            if file_hash_info:
                cylance_file_hash_generalScore = file_hash_info.get(
                    "generalScore", -1.0
                )
                cylance_file_hash_classifiers_ml = file_hash_info.get(
                    "classifiers", {}
                ).get("ml", 0)
                cylance_file_hash_classifiers_human = file_hash_info.get(
                    "classifiers", {}
                ).get("human")
                cylance_file_hash_classifiers_industry = file_hash_info.get(
                    "classifiers", {}
                ).get("industry")

        if webroot_entity:
            webroot_entity = webroot_entity.get("entity", {})
            if webroot_entity:
                webroot_file_hash_category = webroot_entity.get("category")
                webroot_file_hash_malwareCategory = webroot_entity.get(
                    "malwareCategory"
                )
                webroot_file_hash_fileSizeBytes = webroot_entity.get("fileSizeBytes")
                webroot_file_hash_fileLastSeen = webroot_entity.get("fileLastSeen")
                webroot_file_hash_sourceUrls = webroot_entity.get("sourceUrls")

        link = RESULT_LINK.format(file_hash)
        return Hash(
            raw_data,
            link,
            cylance_file_hash_generalScore,
            cylance_file_hash_classifiers_ml,
            cylance_file_hash_classifiers_human,
            cylance_file_hash_classifiers_industry,
            webroot_file_hash_category,
            webroot_file_hash_malwareCategory,
            webroot_file_hash_fileSizeBytes,
            webroot_file_hash_fileLastSeen,
            webroot_file_hash_sourceUrls,
        )

    def build_url_object(self, url_data_entities, url):
        """
        Builds URL data object
        :param url_data_entities: The URL data entities
        :param url: URL for creating the link
        :return: The URL object or None
        """
        webroot_domain_entity = None

        for url_data in url_data_entities:
            enitity_type = url_data.get("type")
            if enitity_type == self.entityTypes.DOMAIN_WHOIS:
                webroot_domain_entity = url_data
                break

        if not webroot_domain_entity:
            return None

        webroot_domain_timesLabeledAsThreat = None
        webroot_domain_age = None
        webroot_domain_popularity = None
        webroot_domain_reputation = None
        webroot_domain_threatCategories = None

        domain_entities = []
        for url_entity in url_data_entities:
            url_data = url_entity.get("entity", {}).get("domain")
            if url.lower() == url_data.lower():
                domain_entities.append(url_entity)

        raw_data = {"content": domain_entities}
        webroot_domain_entity = webroot_domain_entity.get("entity", {})
        if webroot_domain_entity:
            webroot_domain_timesLabeledAsThreat = webroot_domain_entity.get(
                "threatHistory", 0
            )
            webroot_domain_age = webroot_domain_entity.get("age", 0)
            webroot_domain_popularity = webroot_domain_entity.get("popularity", "")
            webroot_domain_reputation = webroot_domain_entity.get("reputation", 0)
            webroot_domain_threatCategories = webroot_domain_entity.get(
                "threatCategories", []
            )

        link = RESULT_LINK.format(url)
        return Url(
            raw_data,
            link,
            webroot_domain_timesLabeledAsThreat,
            webroot_domain_age,
            webroot_domain_popularity,
            webroot_domain_reputation,
            webroot_domain_threatCategories,
        )

    def build_ip_object(self, ip_data_entities, url):
        """
        Builds IP data object
        :param ip_data_entities: The IP data entities
        :param ip: Ip for creating the link
        :return: The IP object or None
        """
        webroot_ip_entity = None

        for ip_data in ip_data_entities:
            enitity_type = ip_data.get("type")
            if enitity_type == self.entityTypes.WEBROOT_IP:
                webroot_ip_entity = ip_data
                break

        if not webroot_ip_entity:
            return None

        webroot_ip_reputationScore = None
        webroot_ip_asn = None
        webroot_ip_currentlyClassifiedAsThreat = None
        webroot_ip_ipThreatHistory = None
        webroot_ip_country = None
        webroot_ip_region = None
        webroot_ip_state = None
        webroot_ip_city = None

        raw_data = {"content": ip_data_entities}
        webroot_ip_entity = webroot_ip_entity.get("entity", {})
        if webroot_ip_entity:
            webroot_ip_reputationScore = webroot_ip_entity.get("reputationScore", 0)
            webroot_ip_asn = webroot_ip_entity.get("asn", 0)
            webroot_ip_currentlyClassifiedAsThreat = webroot_ip_entity.get(
                "currentlyClassifiedAsThreat", False
            )
            webroot_ip_ipThreatHistory = webroot_ip_entity.get("ipThreatHistory", [])
            if webroot_ip_ipThreatHistory:
                webroot_ip_ipThreatHistory = DigitalShadowsParser.prepare_list_for_csv(
                    webroot_ip_ipThreatHistory
                )
            webroot_ip_country = webroot_ip_entity.get("ipGeoInfo", {}).get(
                "country", ""
            )
            webroot_ip_region = webroot_ip_entity.get("ipGeoInfo", {}).get("region", "")
            webroot_ip_state = webroot_ip_entity.get("ipGeoInfo", {}).get("state", "")
            webroot_ip_city = webroot_ip_entity.get("ipGeoInfo", {}).get("city", "")
        link = RESULT_LINK.format(url)
        return Ip(
            raw_data,
            link,
            webroot_ip_reputationScore,
            webroot_ip_asn,
            webroot_ip_currentlyClassifiedAsThreat,
            webroot_ip_ipThreatHistory,
            webroot_ip_country,
            webroot_ip_region,
            webroot_ip_state,
            webroot_ip_city,
        )

    def build_cve_object(self, cve_data_entities, cve):
        """
        Builds CVE data object
        :param cve_data_entities: The CVE data entities
        :param cve: CVE for creating the link
        :return: The CVE object or None
        """
        exploit_entity = None
        vulnerability_entity = None

        for cve_data in cve_data_entities:
            enitity_type = cve_data.get("type")

            if exploit_entity is None and enitity_type == self.entityTypes.EXPLOIT:
                exploit_entity = cve_data
            if (
                vulnerability_entity is None
                and enitity_type == self.entityTypes.VULNERABILITY
            ):
                vulnerability_entity = cve_data

            if exploit_entity and vulnerability_entity:
                break

        if not exploit_entity and not vulnerability_entity:
            return None

        exploit_title = None
        exploit_type = None
        exploit_platform = None
        exploit_sourceUrl = None
        vulnerability_description = None
        vulnerability_sourceUrl = None
        vulnerability_score = None
        vulnerability_authentication = None
        vulnerability_accessVector = None
        vulnerability_accessComplexity = None
        vulnerability_confidentialityImpact = None
        vulnerability_integrityImpact = None
        vulnerability_availabilityImpact = None

        raw_data = {"content": cve_data_entities}
        if exploit_entity:
            exploit_entity = exploit_entity.get("entity")
            if exploit_entity:
                exploit_title = exploit_entity.get("title", "")
                exploit_type = exploit_entity.get("type", "")
                exploit_platform = exploit_entity.get("platform", "")
                exploit_sourceUrl = exploit_entity.get("sourceUri", "")

        if vulnerability_entity:
            vulnerability_entity = vulnerability_entity.get("entity")
            if vulnerability_entity:
                vulnerability_description = vulnerability_entity.get("description", "")
                vulnerability_sourceUrl = vulnerability_entity.get("sourceUri", "")
                vulnerability_score = vulnerability_entity.get("cvss2Score", {}).get(
                    "baseScore"
                )
                vulnerability_authentication = vulnerability_entity.get(
                    "cvss2Score", {}
                ).get("authentication")
                vulnerability_accessVector = vulnerability_entity.get(
                    "cvss2Score", {}
                ).get("accessVector")
                vulnerability_accessComplexity = vulnerability_entity.get(
                    "cvss2Score", {}
                ).get("accessComplexity")
                vulnerability_confidentialityImpact = vulnerability_entity.get(
                    "cvss2Score", {}
                ).get("confidentialityImpact")
                vulnerability_integrityImpact = vulnerability_entity.get(
                    "cvss2Score", {}
                ).get("integrityImpact")
                vulnerability_availabilityImpact = vulnerability_entity.get(
                    "cvss2Score", {}
                ).get("availabilityImpact")
        link = RESULT_LINK.format(cve)
        links = [link]
        return Cve(
            raw_data,
            links,
            exploit_title,
            exploit_type,
            exploit_platform,
            exploit_sourceUrl,
            vulnerability_description,
            vulnerability_sourceUrl,
            vulnerability_score,
            vulnerability_authentication,
            vulnerability_accessVector,
            vulnerability_accessComplexity,
            vulnerability_confidentialityImpact,
            vulnerability_integrityImpact,
            vulnerability_availabilityImpact,
        )

    @staticmethod
    def prepare_list_for_csv(items):
        return [DigitalShadowsParser.join_nested_array(item) for item in items]

    @staticmethod
    def join_nested_array(input_dict):
        response = {}
        for key in list(input_dict.keys()):
            value = input_dict.get(key)
            if isinstance(value, list):
                if not value:
                    continue
                if isinstance(value[0], str):
                    value = " | ".join(value)
            response[key] = value
        return response

    def build_incident_object(self, incident_json):
        return Incident(
            raw_data=incident_json,
            id=incident_json.get("id"),
            title=incident_json.get("title").strip("\n").strip("\r"),
            description=incident_json.get("description"),
            severity=incident_json.get("severity"),
            type=incident_json.get("type"),
            published=incident_json.get("published"),
            mitigation=incident_json.get("mitigation"),
            entity_type=incident_json.get("entitySummary", {}).get("type"),
            entity_source=incident_json.get("entitySummary", {}).get("source"),
        )
