from __future__ import annotations
from TIPCommon import dict_to_flat, add_prefix_to_dict
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
import uuid
from .consts import (
    DEVICE_VENDOR,
    SEVERITY_TO_SIEM_MAPPING,
    YELLOW_COLOR,
    RED_COLOR,
    GREEN_COLOR,
)


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_csv(self):
        return dict_to_flat(self.to_json())

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class CommentObject(BaseModel):

    def __init__(
        self, raw_data, comment_id, comment_row, content, creation_date, commenter
    ):
        super(CommentObject, self).__init__(raw_data)

        self.comment_row = comment_row
        self.comment_id = comment_id
        self.content = content
        self.creation_date = creation_date
        self.commenter = commenter

    def to_table(self):
        table = {
            "Comment Row": self.comment_row,
            "Comment ID": self.comment_id,
            "Content ": self.content,
            "Creation Date": self.creation_date,
            "Commenter ": self.commenter,
        }
        return table


class EntityObject(BaseModel):

    def __init__(self, raw_data, module_name, url, title, creation_date, labels):
        super(EntityObject, self).__init__(raw_data)

        self.module_name = module_name
        self.url = url
        self.labels = labels
        self.creation_date = creation_date
        self.title = title

    def to_table(self):
        table = {
            "Module Name": self.module_name,
            "URL": self.url,
            "Title": self.title,
            "Labels": self.labels,
            "Created At": self.creation_date,
        }
        return table


class LabelsObject(BaseModel):

    def __init__(self, raw_data, label_id, label_name, label_module_id):
        super(LabelsObject, self).__init__(raw_data)
        self.label_id = label_id
        self.label_name = label_name
        self.label_module_id = label_module_id


class ThreatObject(BaseModel):

    def __init__(
        self,
        raw_data,
        id,
        module_id,
        module_type,
        title,
        module_name,
        created_at,
        changed_at,
        labels,
    ):
        super(ThreatObject, self).__init__(raw_data)
        self.id = id
        self.module_id = module_id
        self.module_type = module_type
        self.title = title
        self.module_name = module_name
        self.created_at = created_at
        self.changed_at = changed_at
        self.labels = labels

    def to_alert_info(self, environment, severity, events):
        # type: (EnvironmentHandle, str, list) -> AlertInfo
        """
        Creates Siemplify Alert Info based on Indicator information
        @param environment: EnvironmentHandle object
        @param severity: Severity value for Alert
        @param events: Events list for Alert
        @return: Alert Info object
        """
        alert_info = AlertInfo()
        alert_info.ticket_id = self.id
        alert_info.display_id = str(uuid.uuid4())
        alert_info.name = (
            self.title if self.title else f"{DEVICE_VENDOR} {self.module_name} Alert"
        )
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = self.module_name
        alert_info.priority = SEVERITY_TO_SIEM_MAPPING.get(severity, -1)
        alert_info.rule_generator = (
            f"{DEVICE_VENDOR} {self.module_type.capitalize()} Feed"
        )
        alert_info.start_time = self.changed_at
        alert_info.end_time = self.changed_at
        alert_info.events = [dict_to_flat(event) for event in events]
        alert_info.environment = environment.get_environment(self.raw_data)

        return alert_info

    def to_main_event(self):
        self.raw_data["event_type"] = self.module_type
        return self.raw_data


class ExtraDataObject(BaseModel):
    def __init__(self, raw_data, module_type):
        super(ExtraDataObject, self).__init__(raw_data)
        self.module_type = module_type

    def to_event(self):
        self.raw_data["event_type"] = f"{self.module_type} related ExtraData"
        self.raw_data.get("map", {}).pop("Content", None)
        return self.raw_data


class MalwareObject(BaseModel):
    def __init__(
        self,
        raw_data,
        id,
        hosts,
        module_id,
        module_type,
        title,
        module_name,
        created_at,
        changed_at,
        checked_at,
    ):
        super(MalwareObject, self).__init__(raw_data)
        self.id = id
        self.hosts = hosts
        self.module_id = module_id
        self.module_type = module_type
        self.title = title
        self.module_name = module_name
        self.created_at = created_at
        self.changed_at = changed_at
        self.checked_at = checked_at

    def to_event(self):
        if all(
            value is None
            for value in [self.created_at, self.changed_at, self.checked_at]
        ):
            self.raw_data["event_type"] = (
                f"{self.module_type} related ExtraData - User Submitted"
            )
            for key in [
                "url",
                "title",
                "contentType",
                "countriesId",
                "analysisResult",
                "analysisUserResult",
                "analysisCalcResult",
                "createdAt",
                "checkedAt",
                "changedAt",
            ]:
                self.raw_data.pop(key, None)
            return self.raw_data

        self.raw_data["event_type"] = f"{self.module_type} related ExtraData"
        return self.raw_data


class IPObject(BaseModel):
    def __init__(
        self,
        raw_data,
        id,
        asn_number,
        asn_owner,
        tags,
        latitude,
        longtitude,
        tlp,
        last_seen,
        first_seen,
        risk,
        link,
    ):
        super(IPObject, self).__init__(raw_data)
        self.id = id
        self.asn_number = asn_number
        self.asn_owner = asn_owner
        self.latitude = latitude
        self.longtitude = longtitude
        self.tlp = tlp
        self.last_seen = last_seen
        self.first_seen = first_seen
        self.risk = risk
        self.tags = tags
        self.link = link

    def to_table(self):
        table_data = {
            "id": self.id,
            "asn_number": self.asn_number,
            "asn_owner": self.asn_owner,
            "latitude": self.latitude,
            "longtitude": self.longtitude,
            "tlp": self.tlp,
            "last_seen": self.last_seen,
            "first_seen": self.first_seen,
            "risk": self.risk,
            "tags": self.tags,
            "link": self.link,
        }

        return {key: value for key, value in table_data.items() if value}

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.to_table())
        return add_prefix_to_dict(data, prefix) if prefix else data

    def to_insight(self, identifier):
        content = f"<br><strong>Entity:</strong> {identifier}<br>"
        content += "<body>"
        status_color = YELLOW_COLOR

        if self.risk >= 0 and self.risk < 3:
            status_color = GREEN_COLOR

        if self.risk >= 3 and self.risk < 7:
            status_color = YELLOW_COLOR

        if self.risk >= 7 and self.risk <= 10:
            status_color = RED_COLOR

        content += f'<br><span style="font-weight: 400;"><strong>Score:</strong><span style="color: {status_color};"><strong> {self.risk  or "N/A"}</strong></span></span>'
        content += f'<br><strong>ASN Number:</strong> {self.asn_number  or "N/A"}'
        content += f'<br><strong>ASN Owner:</strong> {self.asn_owner  or "N/A"}'
        content += f'<br><strong>Latitude:</strong> {self.latitude  or "N/A"}'
        content += f'<br><strong>Longtitude:</strong> {self.longtitude  or "N/A"}'
        content += f'<br><strong>TLP:</strong> {self.tlp  or "N/A"}'
        content += f'<br><strong>Tags:</strong> {self.tags  or "N/A"}'
        content += f'<br><strong>Last Seen:</strong> {self.last_seen  or "N/A"}'
        content += f'<br><strong>First Seen:</strong> {self.first_seen  or "N/A"}'
        content += "<br>"
        content += f'<br><strong>Source: </strong><a href={self.link} target="_blank">{self.link  or "N/A"}</a>'
        content += "</body>"
        content += "<p>&nbsp;</p>"

        return content


class HashObject(BaseModel):
    def __init__(
        self,
        raw_data,
        id,
        filetype,
        subtype,
        md5,
        sha1,
        sha256,
        sha512,
        sources_representation,
        tlp,
        last_seen,
        first_seen,
        risk,
        tags,
        link,
    ):
        super(HashObject, self).__init__(raw_data)
        self.id = id
        self.filetype = filetype
        self.subtype = subtype
        self.md5 = md5
        self.sha1 = sha1
        self.sha256 = sha256
        self.sha512 = sha512
        self.sources_representation = sources_representation
        self.tlp = tlp
        self.last_seen = last_seen
        self.first_seen = first_seen
        self.risk = risk
        self.tags = tags
        self.link = link

    def to_table(self):
        table_data = {
            "id": self.id,
            "filetype": self.filetype,
            "subtype": self.subtype,
            "md5": self.md5,
            "sha1": self.sha1,
            "sha256": self.sha256,
            "sha512": self.sha512,
            "sources_representation": self.sources_representation,
            "tlp": self.tlp,
            "last_seen": self.last_seen,
            "first_seen": self.first_seen,
            "risk": self.risk,
            "tags": self.tags,
            "link": self.link,
        }

        return {key: value for key, value in table_data.items() if value}

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.to_table())
        return add_prefix_to_dict(data, prefix) if prefix else data

    def to_insight(self, identifier):
        content = f"<br><strong>Entity:</strong> {identifier}<br>"
        content += "<body>"
        status_color = YELLOW_COLOR

        if self.risk >= 0 and self.risk < 3:
            status_color = GREEN_COLOR

        if self.risk >= 3 and self.risk < 7:
            status_color = YELLOW_COLOR

        if self.risk >= 7 and self.risk <= 10:
            status_color = RED_COLOR

        content += f'<br><strong>Score:</strong><span style="color: {status_color};"><strong> {self.risk  or "N/A"}</strong></span>'
        content += f'<br><strong>File Type:</strong> {self.filetype  or "N/A"}'
        content += f'<br><strong>Subtype:</strong> {self.subtype  or "N/A"}'
        content += f'<br><strong>Date Sources:</strong> {self.sources_representation  or "N/A"}'
        content += f'<br><strong>TLP:</strong> {self.tlp  or "N/A"}'
        content += f'<br><strong>Tags:</strong> {self.tags  or "N/A"}'
        content += f'<br><strong>Last Seen:</strong> {self.last_seen  or "N/A"}'
        content += f'<br><strong>First Seen:</strong> {self.first_seen  or "N/A"}'
        content += "<br>"
        content += f'<br><strong>Source: </strong><a href={self.link} target="_blank">{self.link  or "N/A"}</a>'
        content += "</body>"
        content += "<p>&nbsp;</p>"

        return content


class URLObject(BaseModel):
    def __init__(
        self,
        raw_data,
        id,
        bots_count,
        credentials_count,
        credit_cards_count,
        status,
        main_type,
        tlp,
        last_seen,
        first_seen,
        risk,
        tags,
        link,
    ):
        super(URLObject, self).__init__(raw_data)
        self.id = id
        self.bots_count = bots_count
        self.credentials_count = credentials_count
        self.credit_cards_count = credit_cards_count
        self.status = status
        self.main_type = main_type
        self.tlp = tlp
        self.last_seen = last_seen
        self.first_seen = first_seen
        self.risk = risk
        self.tags = tags
        self.link = link

    def to_table(self):
        table_data = {
            "id": self.id,
            "bots_count": self.bots_count,
            "credentials_count": self.credentials_count,
            "credit_cards_count": self.credit_cards_count,
            "status": self.status,
            "main_type": self.main_type,
            "tlp": self.tlp,
            "last_seen": self.last_seen,
            "first_seen": self.first_seen,
            "risk": self.risk,
            "tags": self.tags,
            "link": self.link,
        }

        return {key: value for key, value in table_data.items() if value}

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.to_table())
        return add_prefix_to_dict(data, prefix) if prefix else data

    def to_insight(self, identifier):
        content = f"<br><strong>Entity:</strong> {identifier}<br>"
        content += "<body>"
        status_color = YELLOW_COLOR

        if self.risk >= 0 and self.risk < 3:
            status_color = GREEN_COLOR

        if self.risk >= 3 and self.risk < 7:
            status_color = YELLOW_COLOR

        if self.risk >= 7 and self.risk <= 10:
            status_color = RED_COLOR

        content += f'<br><strong>Score:</strong><span style="color: {status_color};"><strong> {self.risk  or "N/A"}</strong></span>'
        content += f'<br><strong>Type:</strong> {self.main_type  or "N/A"}'
        content += f'<br><strong>TLP:</strong> {self.tlp  or "N/A"}'
        content += f'<br><strong>Last Seen:</strong> {self.last_seen  or "N/A"}'
        content += f'<br><strong>First Seen:</strong> {self.first_seen  or "N/A"}'
        content += "<br>"
        content += f'<br><strong>Source: </strong><a href={self.link} target="_blank">{self.link  or "N/A"}</a>'
        content += "</body>"
        content += "<p>&nbsp;</p>"

        return content


class CVEObject(BaseModel):
    def __init__(
        self,
        raw_data,
        id,
        bl_score,
        cvss_v2_accessComplexity,
        cvss_v2_accessVector,
        cvss_v2_authentication,
        cvss_v2_availabilityImpact,
        cvss_v2_baseScore,
        cvss_v2_confidentialityImpact,
        cvss_v2_integrityImpact,
        cvss_v2_vectorString,
        cvss_v3_accessComplexity,
        cvss_v3_accessVector,
        cvss_v3_privilegesRequired,
        cvss_v3_availabilityImpact,
        cvss_v3_baseScore,
        cvss_v3_integrityImpact,
        cvss_v3_vectorString,
        cvss_v3_scope,
        cvss_v3_userInteraction,
        exploits_name,
        status,
        remote,
        score,
        tlp,
        tags,
        updated_at,
        created_at,
        link,
        cvss_v3_baseSeverity,
        cvss_v3_confidentialityImpact,
    ):
        super(CVEObject, self).__init__(raw_data)
        self.id = id
        self.bl_score = bl_score
        self.cvss_v2_accessComplexity = cvss_v2_accessComplexity
        self.cvss_v2_accessVector = cvss_v2_accessVector
        self.cvss_v2_authentication = cvss_v2_authentication
        self.cvss_v2_availabilityImpact = cvss_v2_availabilityImpact
        self.cvss_v2_baseScore = cvss_v2_baseScore
        self.cvss_v2_confidentialityImpact = cvss_v2_confidentialityImpact
        self.cvss_v2_integrityImpact = cvss_v2_integrityImpact
        self.cvss_v2_vectorString = cvss_v2_vectorString
        self.cvss_v3_accessComplexity = cvss_v3_accessComplexity
        self.cvss_v3_accessVector = cvss_v3_accessVector
        self.cvss_v3_privilegesRequired = cvss_v3_privilegesRequired
        self.cvss_v3_availabilityImpact = cvss_v3_availabilityImpact
        self.cvss_v3_baseScore = cvss_v3_baseScore
        self.cvss_v3_baseSeverity = cvss_v3_baseSeverity
        self.cvss_v3_confidentialityImpact = cvss_v3_confidentialityImpact
        self.cvss_v3_integrityImpact = cvss_v3_integrityImpact
        self.cvss_v3_vectorString = cvss_v3_vectorString
        self.cvss_v3_scope = cvss_v3_scope
        self.cvss_v3_userInteraction = cvss_v3_userInteraction
        self.exploits_name = exploits_name
        self.status = status
        self.remote = remote
        self.score = score
        self.tlp = tlp
        self.tags = tags
        self.updated_at = updated_at
        self.created_at = created_at
        self.link = link

    def to_table(self):
        table_data = {
            "id": self.id,
            "bl_score": self.bl_score,
            "cvss_v2_accessComplexity": self.cvss_v2_accessComplexity,
            "cvss_v2_accessVector": self.cvss_v2_accessVector,
            "cvss_v2_authentication": self.cvss_v2_authentication,
            "cvss_v2_availabilityImpact": self.cvss_v2_availabilityImpact,
            "cvss_v2_baseScore": self.cvss_v2_baseScore,
            "cvss_v2_confidentialityImpact": self.cvss_v2_confidentialityImpact,
            "cvss_v2_integrityImpact": self.cvss_v2_integrityImpact,
            "cvss_v2_vectorString": self.cvss_v2_vectorString,
            "cvss_v3_accessComplexity": self.cvss_v3_accessComplexity,
            "cvss_v3_accessVector": self.cvss_v3_accessVector,
            "cvss_v3_privilegesRequired": self.cvss_v3_privilegesRequired,
            "cvss_v3_availabilityImpact": self.cvss_v3_availabilityImpact,
            "cvss_v3_baseScore": self.cvss_v3_baseScore,
            "cvss_v3_confidentialityImpact": self.cvss_v3_confidentialityImpact,
            "cvss_v3_baseSeverity": self.cvss_v3_baseSeverity,
            "cvss_v3_integrityImpact": self.cvss_v3_integrityImpact,
            "cvss_v3_vectorString": self.cvss_v3_vectorString,
            "cvss_v3_scope": self.cvss_v3_scope,
            "cvss_v3_userInteraction": self.cvss_v3_userInteraction,
            "exploits_name": self.exploits_name,
            "status": self.status,
            "remote": self.remote,
            "score": self.score,
            "tlp": self.tlp,
            "tags": self.tags,
            "updated_at": self.updated_at,
            "created_at": self.created_at,
            "link": self.link,
        }

        return {key: value for key, value in table_data.items() if value}

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.to_table())
        return add_prefix_to_dict(data, prefix) if prefix else data

    def to_insight(self, identifier):
        content = f"<br><strong>Entity:</strong> {identifier}<br>"
        content += "<body>"

        status_color = YELLOW_COLOR

        if self.score >= 0 and self.score < 3:
            status_color = GREEN_COLOR

        if self.score >= 3 and self.score < 7:
            status_color = YELLOW_COLOR

        if self.score >= 7 and self.score <= 10:
            status_color = RED_COLOR

        content += f'<br><strong>Score:</strong><span style="color: {status_color};"><strong> {self.score  or "N/A"}</strong></span>'
        content += f'<br><strong>Status:</strong> {self.status  or "N/A"}'
        content += f'<br><strong>Remote:</strong> {self.remote  or "N/A"}'
        content += (
            f'<br><strong>Related Exploits:</strong> {self.exploits_name  or "N/A"}'
        )
        content += f'<br><strong>TLP:</strong> {self.tlp  or "N/A"}'
        content += f'<br><strong>Tags:</strong> {self.tags  or "N/A"}'
        content += f'<br><strong>Created At:</strong> {self.created_at  or "N/A"}'
        content += f'<br><strong>Updated At:</strong> {self.updated_at  or "N/A"}'
        content += "<br>"
        content += '<br><span style="font-weight: 400;">CVSS V2</span>'
        content += "<br>"
        content += f'<br><strong>Access Complexity:</strong> {self.cvss_v2_accessComplexity  or "N/A"}'
        content += (
            f'<br><strong>Access Vector:</strong> {self.cvss_v2_accessVector  or "N/A"}'
        )
        content += f'<br><strong>Authentication:</strong> {self.cvss_v2_authentication  or "N/A"}'
        content += f'<br><strong>Availability Impact:</strong> {self.cvss_v2_availabilityImpact  or "N/A"}'
        content += (
            f'<br><strong>Base Score:</strong> {self.cvss_v2_baseScore  or "N/A"}'
        )
        content += f'<br><strong>Confidentiality Impact:</strong> {self.cvss_v2_confidentialityImpact  or "N/A"}'
        content += f'<br><strong>Integrity Impact:</strong> {self.cvss_v2_integrityImpact  or "N/A"}'
        content += "<br>"
        content += '<br><span style="font-weight: 400;">CVSS V3</span>'
        content += "<br>"
        content += f'<br><strong>Access Complexity:</strong> {self.cvss_v3_accessComplexity  or "N/A"}'
        content += (
            f'<br><strong>Access Vector:</strong> {self.cvss_v3_accessVector  or "N/A"}'
        )
        content += f'<br><strong>Privileges Required:</strong> {self.cvss_v3_privilegesRequired  or "N/A"}'
        content += f'<br><strong>Availability Impact:</strong> {self.cvss_v2_availabilityImpact  or "N/A"}'
        content += (
            f'<br><strong>Base Score:</strong> {self.cvss_v2_baseScore  or "N/A"}'
        )
        content += (
            f'<br><strong>Base Severity:</strong> {self.cvss_v3_baseSeverity  or "N/A"}'
        )
        content += f'<br><strong>Confidentiality Impact:</strong> {self.cvss_v3_confidentialityImpact  or "N/A"}'
        content += f'<br><strong>Scope:</strong> {self.cvss_v3_scope  or "N/A"}'
        content += f'<br><strong>User Interaction:</strong> {self.cvss_v3_userInteraction  or "N/A"}'
        content += f'<br><strong>Integrity Impact:</strong> {self.cvss_v3_integrityImpact  or "N/A"}'
        content += "</body>"
        content += "<p>&nbsp;</p>"

        return content


class ThreatActorObject(BaseModel):
    def __init__(
        self,
        raw_data,
        id,
        active,
        aliases,
        country_name,
        status,
        modus_operandi,
        objective,
        tlp,
        last_seen,
        first_seen,
        sophistication,
        types,
        link,
    ):
        super(ThreatActorObject, self).__init__(raw_data)
        self.id = id
        self.active = active
        self.aliases = aliases
        self.country_name = country_name
        self.status = status
        self.modus_operandi = modus_operandi
        self.objective = objective
        self.tlp = tlp
        self.last_seen = last_seen
        self.first_seen = first_seen
        self.sophistication = sophistication
        self.types = types
        self.link = link

    def to_table(self):
        table_data = {
            "id": self.id,
            "active": self.active,
            "aliases": self.aliases,
            "country_name": self.country_name,
            "modus_operandi ": self.modus_operandi,
            "objective": self.objective,
            "tlp": self.tlp,
            "last_seen": self.last_seen,
            "first_seen": self.first_seen,
            "sophistication": self.sophistication,
            "types": self.types,
            "link": self.link,
        }

        return {key: value for key, value in table_data.items() if value}

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.to_table())
        return add_prefix_to_dict(data, prefix) if prefix else data

    def to_insight(self, identifier):
        content = f"<br><strong>Entity:</strong> {identifier}<br>"
        content += "<body>"
        content += f'<br><span style="font-weight: 400;"><strong>Active:</strong> {self.active  or "N/A"}</span>'
        content += f'<br><strong>Aliases:</strong> {self.aliases  or "N/A"}'
        content += f'<br><strong>Country:</strong> {self.country_name  or "N/A"}'
        content += (
            f'<br><strong>Modus Operandi:</strong> {self.modus_operandi  or "N/A"}'
        )
        content += f'<br><strong>Objective:</strong> {self.objective  or "N/A"}'
        content += (
            f'<br><strong>Sophistication:</strong> {self.sophistication  or "N/A"}'
        )
        content += f'<br><strong>Types:</strong> {self.types  or "N/A"}'
        content += f'<br><strong>TLP:</strong> {self.tlp  or "N/A"}'
        content += f'<br><strong>Last Seen:</strong> {self.last_seen  or "N/A"}'
        content += f'<br><strong>First Seen:</strong> {self.first_seen  or "N/A"}'
        content += "<br>"
        content += f'<br><strong>Source: </strong><a href={self.link} target="_blank">{self.link  or "N/A"}</a>'
        content += "</body>"
        content += "<p>&nbsp;</p>"

        return content


class ThreatCampaignObject(BaseModel):
    def __init__(self, raw_data, id, tlp, last_seen, first_seen, link):
        super(ThreatCampaignObject, self).__init__(raw_data)
        self.id = id
        self.tlp = tlp
        self.last_seen = last_seen
        self.first_seen = first_seen
        self.link = link

    def to_table(self):
        table_data = {
            "id": self.id,
            "tlp": self.tlp,
            "last_seen": self.last_seen,
            "first_seen": self.first_seen,
            "link": self.link,
        }

        return {key: value for key, value in table_data.items() if value}

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.to_table())
        return add_prefix_to_dict(data, prefix) if prefix else data

    def to_insight(self, identifier):
        content = f"<br><strong>Entity:</strong> {identifier}<br>"
        content += "<body>"
        content += f'<br><strong>TLP:</strong> {self.tlp  or "N/A"}'
        content += f'<br><strong>Last Seen:</strong> {self.last_seen  or "N/A"}'
        content += f'<br><strong>First Seen:</strong> {self.first_seen  or "N/A"}'
        content += "<br>"
        content += f'<br><strong>Source: </strong><a href={self.link} target="_blank">{self.link  or "N/A"}</a>'
        content += "</body>"
        content += "<p>&nbsp;</p>"

        return content


class ThreatSignatureObject(BaseModel):
    def __init__(
        self, raw_data, tags, id, signature, status, threat_type, tlp, created_at, link
    ):
        super(ThreatSignatureObject, self).__init__(raw_data)
        self.id = id
        self.signature = signature
        self.status = status
        self.threat_type = threat_type
        self.tlp = tlp
        self.created_at = created_at
        self.link = link
        self.tags = tags

    def to_table(self):
        table_data = {
            "id": self.id,
            "signature": self.signature,
            "status": self.status,
            "type": self.threat_type,
            "tlp": self.tlp,
            "created_at": self.created_at,
            "link": self.link,
        }

        return {key: value for key, value in table_data.items() if value}

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.to_table())
        return add_prefix_to_dict(data, prefix) if prefix else data

    def to_insight(self, identifier):
        content = f"<br><strong>Entity:</strong> {identifier}<br>"
        content += "<body>"
        content += f'<br><span style="font-weight: 400;"><strong>Status:</strong> {self.status  or "N/A"}</span>'
        content += f'<br><strong>Signature:</strong> {self.signature  or "N/A"}'
        content += f'<br><strong>Type:</strong> {self.threat_type  or "N/A"}'
        content += f'<br><strong>TLP:</strong> {self.tlp  or "N/A"}'
        content += f'<br><strong>Tags:</strong> {self.tags  or "N/A"}'
        content += f'<br><strong>Created At:</strong> {self.created_at  or "N/A"}'
        content += "<br>"
        content += f'<br><strong>Source: </strong><a href={self.link} target="_blank">{self.link  or "N/A"}</a>'
        content += "</body>"
        content += "<p>&nbsp;</p>"

        return content


class ThreatObjectDetailsObject(BaseModel):
    def __init__(self, raw_data, id):
        super(ThreatObjectDetailsObject, self).__init__(raw_data)
        self.id = id
