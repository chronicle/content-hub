from __future__ import annotations
import uuid
import copy
from TIPCommon import add_prefix_to_dict, flat_dict_to_csv
from TIPCommon import dict_to_flat as dtf
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from .DigitalShadowsConstants import (
    DEVICE_VENDOR,
    DEVICE_PRODUCT,
    DIGITAL_SHADOWS_TO_SIEM_SEVERITY,
)

ENRICH_PREFIX = "DigitalShadows"


def dict_to_flat(input_dict):
    res = dtf(input_dict)
    for k, v in list(res.items()):
        if isinstance(v, str) or isinstance(v, str) or isinstance(v, str):
            v = v.strip()
            if not v:
                res.pop(k)
    return res


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data


class Hash:
    """
    Hash class keeps information which received from DigitalShadows Hash scanning
    """

    def __init__(
        self,
        raw_data,
        link,
        cylance_file_hash_generalScore=None,
        cylance_file_hash_classifiers_ml=None,
        cylance_file_hash_classifiers_human=None,
        cylance_file_hash_classifiers_industry=None,
        webroot_file_hash_category=None,
        webroot_file_hash_malwareCategory=None,
        webroot_file_hash_fileSizeBytes=None,
        webroot_file_hash_fileLastSeen=None,
        webroot_file_hash_sourceUrls=None,
    ):
        self.raw_data = raw_data
        self.link = link
        self.cylance_file_hash_generalScore = cylance_file_hash_generalScore
        self.cylance_file_hash_classifiers_ml = cylance_file_hash_classifiers_ml
        self.cylance_file_hash_classifiers_human = cylance_file_hash_classifiers_human
        self.cylance_file_hash_classifiers_industry = (
            cylance_file_hash_classifiers_industry
        )
        self.webroot_file_hash_category = webroot_file_hash_category
        self.webroot_file_hash_malwareCategory = webroot_file_hash_malwareCategory
        self.webroot_file_hash_fileSizeBytes = webroot_file_hash_fileSizeBytes
        self.webroot_file_hash_fileLastSeen = webroot_file_hash_fileLastSeen
        self.webroot_file_hash_sourceUrls = webroot_file_hash_sourceUrls

    def to_dict(self):
        ret = {}

        # Constructing cylance_file_hash dict
        cylance_file_hash = {}
        cylance_file_hash_classifier = {}
        if self.cylance_file_hash_generalScore:
            cylance_file_hash["generalScore"] = self.cylance_file_hash_generalScore
        if self.cylance_file_hash_classifiers_ml:
            cylance_file_hash_classifier["ml"] = self.cylance_file_hash_classifiers_ml
        if self.cylance_file_hash_classifiers_industry:
            cylance_file_hash_classifier["industry"] = (
                self.cylance_file_hash_classifiers_industry
            )
        if self.cylance_file_hash_classifiers_human:
            cylance_file_hash_classifier["human"] = (
                self.cylance_file_hash_classifiers_human
            )

        if cylance_file_hash_classifier:
            cylance_file_hash["classifier"] = cylance_file_hash_classifier
        if cylance_file_hash:
            ret["CylanceFileHash"] = cylance_file_hash

        # Constructing webroot_file_hash dict
        webroot_file_hash = {}
        if self.webroot_file_hash_category:
            webroot_file_hash["category"] = self.webroot_file_hash_category
        if self.webroot_file_hash_malwareCategory:
            webroot_file_hash["malwareCategory"] = (
                self.webroot_file_hash_malwareCategory
            )
        if self.webroot_file_hash_fileSizeBytes is not None:  # excluding 0 case
            webroot_file_hash["fileSizeBytes"] = self.webroot_file_hash_fileSizeBytes
        if self.webroot_file_hash_fileLastSeen:
            webroot_file_hash["fileLastSeen"] = self.webroot_file_hash_fileLastSeen
        if self.webroot_file_hash_sourceUrls:
            webroot_file_hash["sourceUrls"] = self.webroot_file_hash_sourceUrls

        if webroot_file_hash:
            ret["WebrootFileHash"] = webroot_file_hash

        return ret

    def to_enrichment_data(self):
        ret_dict = self.to_dict()
        return add_prefix_to_dict(dict_to_flat(ret_dict), ENRICH_PREFIX)

    def to_csv(self):
        ret_dict = self.to_dict()
        ret_dict = dict_to_flat(ret_dict)
        return flat_dict_to_csv(ret_dict)

    def to_json(self):
        return self.raw_data.copy()


class Url:
    """
    URL class keeps information which received from DigitalShadows URL scanning
    """

    def __init__(
        self,
        raw_data,
        link,
        webroot_domain_timesLabeledAsThreat=None,
        webroot_domain_age=None,
        webroot_domain_popularity=None,
        webroot_domain_reputation=None,
        webroot_domain_threatCategories=None,
    ):
        self.raw_data = raw_data
        self.link = link
        self.webroot_domain_timesLabeledAsThreat = webroot_domain_timesLabeledAsThreat
        self.webroot_domain_age = webroot_domain_age
        self.webroot_domain_popularity = webroot_domain_popularity
        self.webroot_domain_reputation = webroot_domain_reputation
        self.webroot_domain_threatCategories = webroot_domain_threatCategories

    def to_dict(self):
        ret = {}
        webrootDomain = {}
        if self.webroot_domain_timesLabeledAsThreat is not None:  # excluding 0 case
            webrootDomain["timesLabeledAsThreat"] = (
                self.webroot_domain_timesLabeledAsThreat
            )
        if self.webroot_domain_age is not None:  # excluding 0 case
            webrootDomain["age"] = self.webroot_domain_age
        if self.webroot_domain_popularity:
            webrootDomain["popularity"] = self.webroot_domain_popularity
        if self.webroot_domain_reputation:
            webrootDomain["reputation"] = self.webroot_domain_reputation
        if self.webroot_domain_threatCategories:
            webrootDomain["threatCategories"] = self.webroot_domain_threatCategories

        if webrootDomain:
            ret["WebrootDomain"] = webrootDomain
        return ret

    def to_enrichment_data(self):
        ret_dict = self.to_dict()
        return add_prefix_to_dict(dict_to_flat(ret_dict), ENRICH_PREFIX)

    def to_csv(self):
        ret_dict = self.to_dict()
        ret_dict = dict_to_flat(ret_dict)
        return flat_dict_to_csv(ret_dict)

    def to_json(self):
        return self.raw_data.copy()


class Ip:
    """
    Ip class keeps information which received from DigitalShadows IP scanning
    """

    def __init__(
        self,
        raw_data,
        link,
        webroot_ip_reputationScore=None,
        webroot_ip_asn=None,
        webroot_ip_currentlyClassifiedAsThreat=None,
        webroot_ip_ipThreatHistory=None,
        webroot_ip_country=None,
        webroot_ip_region=None,
        webroot_ip_state=None,
        webroot_ip_city=None,
    ):
        self.raw_data = raw_data
        self.link = link
        self.webroot_ip_reputationScore = webroot_ip_reputationScore
        self.webroot_ip_asn = webroot_ip_asn
        self.webroot_ip_currentlyClassifiedAsThreat = (
            webroot_ip_currentlyClassifiedAsThreat
        )
        self.webroot_ip_ipThreatHistory = webroot_ip_ipThreatHistory
        self.webroot_ip_country = webroot_ip_country
        self.webroot_ip_region = webroot_ip_region
        self.webroot_ip_state = webroot_ip_state
        self.webroot_ip_city = webroot_ip_city

    def to_dict(self):
        ret = {}
        webrootIP = {}
        if self.webroot_ip_reputationScore:
            webrootIP["reputationScore"] = self.webroot_ip_reputationScore
        if self.webroot_ip_asn:
            webrootIP["asn"] = self.webroot_ip_asn
        if self.webroot_ip_currentlyClassifiedAsThreat:
            webrootIP["currentlyClassifiedAsThreat"] = (
                self.webroot_ip_currentlyClassifiedAsThreat
            )
        if self.webroot_ip_ipThreatHistory:
            webrootIP["ipThreatHistory"] = self.webroot_ip_ipThreatHistory
        if self.webroot_ip_country:
            webrootIP["country"] = self.webroot_ip_country
        if self.webroot_ip_region:
            webrootIP["region"] = self.webroot_ip_region
        if self.webroot_ip_state:
            webrootIP["state"] = self.webroot_ip_state
        if self.webroot_ip_city:
            webrootIP["city"] = self.webroot_ip_city

        if webrootIP:
            ret["WebrootIP"] = webrootIP
        return ret

    def to_enrichment_data(self):
        ret_dict = self.to_dict()
        return add_prefix_to_dict(dict_to_flat(ret_dict), ENRICH_PREFIX)

    def to_csv(self):
        ret_dict = self.to_dict()
        ret_dict = dict_to_flat(ret_dict)
        return flat_dict_to_csv(ret_dict)

    def to_json(self):
        return self.raw_data.copy()


class Cve:
    """
    Cve class keeps information which received from DigitalShadows Cve scanning
    """

    def __init__(
        self,
        raw_data,
        links,
        exploit_title=None,
        exploit_type=None,
        exploit_platform=None,
        exploit_sourceUrl=None,
        vulnerability_description=None,
        vulnerability_sourceUrl=None,
        vulnerability_score=None,
        vulnerability_authentication=None,
        vulnerability_accessVector=None,
        vulnerability_accessComplexity=None,
        vulnerability_confidentialityImpact=None,
        vulnerability_integrityImpact=None,
        vulnerability_availabilityImpact=None,
    ):
        self.raw_data = raw_data
        self.links = links
        self.exploit_title = exploit_title
        self.exploit_type = exploit_type
        self.exploit_platform = exploit_platform
        self.exploit_sourceUrl = exploit_sourceUrl
        self.vulnerability_description = vulnerability_description
        self.vulnerability_sourceUrl = vulnerability_sourceUrl
        self.vulnerability_score = vulnerability_score
        self.vulnerability_authentication = vulnerability_authentication
        self.vulnerability_accessVector = vulnerability_accessVector
        self.vulnerability_accessComplexity = vulnerability_accessComplexity
        self.vulnerability_confidentialityImpact = vulnerability_confidentialityImpact
        self.vulnerability_integrityImpact = vulnerability_integrityImpact
        self.vulnerability_availabilityImpact = vulnerability_availabilityImpact

        if self.exploit_sourceUrl:
            self.links.append(self.exploit_sourceUrl)
        if self.vulnerability_sourceUrl:
            self.links.append(self.vulnerability_sourceUrl)

    def to_dict(self):
        ret = {}
        exploit = {}
        # constructing exploit dict
        if self.exploit_title:
            exploit["title"] = self.exploit_title
        if self.exploit_type:
            exploit["type"] = self.exploit_type
        if self.exploit_platform:
            exploit["platform"] = self.exploit_platform
        if self.exploit_sourceUrl:
            exploit["sourceURL"] = self.exploit_sourceUrl

        if exploit:
            ret["Exploit"] = exploit

        vulnerability = {}
        # constructing vulnerability dict
        if self.vulnerability_description:
            vulnerability["description"] = self.vulnerability_description
        if self.vulnerability_sourceUrl:
            vulnerability["sourceURL"] = self.vulnerability_sourceUrl
        if self.vulnerability_score:
            vulnerability["score"] = self.vulnerability_score
        if self.vulnerability_authentication:
            vulnerability["authentication"] = self.vulnerability_authentication
        if self.vulnerability_accessVector:
            vulnerability["accessVector"] = self.vulnerability_accessVector
        if self.vulnerability_accessComplexity:
            vulnerability["accessComplexity"] = self.vulnerability_accessComplexity
        if self.vulnerability_confidentialityImpact:
            vulnerability["confidentialityImpact"] = (
                self.vulnerability_confidentialityImpact
            )
        if self.vulnerability_integrityImpact:
            vulnerability["integrityImpact"] = self.vulnerability_integrityImpact
        if self.vulnerability_availabilityImpact:
            vulnerability["availabilityImpact"] = self.vulnerability_availabilityImpact

        if vulnerability:
            ret["Vulnerability"] = vulnerability
        return ret

    def to_enrichment_data(self):
        ret_dict = self.to_dict()
        return add_prefix_to_dict(dict_to_flat(ret_dict), ENRICH_PREFIX)

    def to_csv(self):
        ret_dict = self.to_dict()
        ret_dict = dict_to_flat(ret_dict)
        return flat_dict_to_csv(ret_dict)

    def to_json(self):
        return self.raw_data.copy()


class Incident(BaseModel):
    def __init__(
        self,
        raw_data,
        id,
        title,
        description,
        severity,
        type,
        published,
        mitigation,
        entity_type,
        entity_source,
    ):
        super(Incident, self).__init__(raw_data)
        self.id = id
        self.title = title
        self.description = description
        self.severity = severity
        self.type = type
        self.published = published
        self.mitigation = mitigation
        self.entity_type = entity_type
        self.entity_source = entity_source

    @property
    def priority(self):
        """
        Converts API severity format to SIEM priority
        @return: SIEM priority
        """
        return DIGITAL_SHADOWS_TO_SIEM_SEVERITY.get(self.severity, -1)

    def to_alert_info(self, environment):
        """
        Creates Siemplify Alert Info based on Indicator information
        @param environment: EnvironmentHandle object
        @return: Alert Info object
        """
        alert_info = AlertInfo()
        alert_info.ticket_id = self.id
        alert_info.display_id = str(uuid.uuid4())
        alert_info.name = self.title
        alert_info.description = self.description
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = DEVICE_PRODUCT
        alert_info.priority = self.priority
        alert_info.rule_generator = self.type
        alert_info.start_time = convert_string_to_unix_time(self.published)
        alert_info.end_time = convert_string_to_unix_time(self.published)
        alert_info.events = [self.to_event()]
        alert_info.environment = environment.get_environment(self.raw_data)
        alert_info.extensions = dict_to_flat({"mitigation": self.mitigation})

        return alert_info

    def to_event(self):
        event = copy.deepcopy(self.raw_data)
        event_summary = event.get("entitySummary", {})
        if self.entity_type.lower() not in event_summary:
            event_summary[self.entity_type] = self.entity_source
        event["entitySummary"] = event_summary
        return dict_to_flat(event)
