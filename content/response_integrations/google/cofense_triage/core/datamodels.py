from __future__ import annotations
import uuid
from TIPCommon.transformation import dict_to_flat, add_prefix_to_dict
from .constants import CONFENSE_TRIAGE_PREFIX, DEVICE_VENDOR, DEVICE_PRODUCT
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from urllib.parse import urljoin
from .UtilsManager import convert_list_to_comma_string


url_event_name = "Related URL"
url_event_description = "This is a custom event that contains information about the URL that it is related to the email"
hostname_event_name = "Related Domain"
hostname_event_description = (
    "This is a custom event that contains information about the domain that it is related to"
    " the email"
)
threat_indicator_event_name = "Related Threat Indicator"
threat_indicator_event_description = (
    "This is a custom event that contains information about the threat indicator"
    " that it is related to the email"
)
attachment_event_name = "Related Attachment"
attachment_event_description = (
    "This is a custom event that contains information about the attachment that it is "
    "related to the email"
)
comment_event_name = "Related Comments"
comment_event_description = (
    "This is a custom event that contains information about the comment that it is related "
    "to the email"
)
header_event_name = "Related Headers"
header_event_description = (
    "This is a custom event that contains information about the headers that are related "
    "to the email"
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


class URLObject(BaseModel):

    def __init__(
        self,
        raw_data,
        risk_score,
        url,
        created_at,
        updated_at,
        attributes,
        url_id,
        url_type,
    ):
        super(URLObject, self).__init__(raw_data)
        self.risk_score = risk_score
        self.url = url
        self.created_at = created_at
        self.updated_at = updated_at
        self.attributes = attributes
        self.url_type = url_type
        self.url_id = url_id

    def as_enrichment_data(self):
        enrichment_data = {}
        if self.risk_score:
            enrichment_data["risk_score"] = self.risk_score

        if self.created_at:
            enrichment_data["created_at"] = self.created_at

        if self.updated_at:
            enrichment_data["updated_at"] = self.updated_at

        if self.url_id:
            enrichment_data["id"] = self.url_id

        return add_prefix_to_dict(dict_to_flat(enrichment_data), CONFENSE_TRIAGE_PREFIX)

    def to_table(self):
        """
        Function that prepares the users's data to be used on the table
        :return {list} List containing dict of users's data
        """

        table_data_list = []

        table_data = {}
        if self.risk_score:
            table_data["risk_score"] = self.risk_score

        if self.created_at:
            table_data["created_at"] = self.created_at

        if self.updated_at:
            table_data["updated_at"] = self.updated_at

        if self.url_id:
            table_data["id"] = self.url_id

        for key, value in table_data.items():
            table_data_list.append({"Key": key, "Value": value})

        return table_data_list

    def to_json(self):

        json_data = {}
        if self.url_id:
            json_data["id"] = self.url_id

        if self.url_type:
            json_data["type"] = self.url_type

        if self.attributes:
            json_data["attributes"] = self.attributes

        return json_data


class UniversalObject(BaseModel):

    def __init__(self, raw_data, data_id, data_type, attributes):
        super(UniversalObject, self).__init__(raw_data)
        self.data_id = data_id
        self.data_type = data_type
        self.attributes = attributes

    def to_json(self):

        json_data = {}
        if self.data_id:
            json_data["id"] = self.data_id

        if self.data_type:
            json_data["type"] = self.data_type

        if self.attributes:
            json_data["attributes"] = self.attributes

        return json_data


class DomainDetailsObject(BaseModel):

    def __init__(self, raw_data, data_id, data_type, attributes, risk_score, hostname):
        super(DomainDetailsObject, self).__init__(raw_data)
        self.data_id = data_id
        self.data_type = data_type
        self.attributes = attributes
        self.risk_score = risk_score
        self.hostname = hostname

    def to_json(self):

        json_data = {}
        if self.data_id:
            json_data["id"] = self.data_id

        if self.data_type:
            json_data["type"] = self.data_type

        if self.attributes:
            json_data["attributes"] = self.attributes

        return json_data

    def to_table(self):
        table = {"Name": self.hostname, "Risk Score": self.risk_score}
        return table


class ReportReportersObject(BaseModel):

    def __init__(
        self,
        raw_data,
        data_id,
        data_type,
        attributes,
        email,
        reports_count,
        reputation_score,
        vip,
    ):
        super(ReportReportersObject, self).__init__(raw_data)
        self.data_id = data_id
        self.data_type = data_type
        self.attributes = attributes
        self.email = email
        self.reports_count = reports_count
        self.reputation_score = reputation_score
        self.vip = vip

    def to_json(self):

        json_data = {}
        if self.data_id:
            json_data["id"] = self.data_id

        if self.data_type:
            json_data["type"] = self.data_type

        if self.attributes:
            json_data["attributes"] = self.attributes

        return json_data

    def to_table(self):
        table = {
            "Email": self.email,
            "Reports Count": self.reports_count,
            "Reputation Score": self.reputation_score,
            "VIP": self.vip,
        }
        return table


class ReportHeadersObject(BaseModel):

    def __init__(self, raw_data, data_id, data_type, attributes, key, value):
        super(ReportHeadersObject, self).__init__(raw_data)
        self.data_id = data_id
        self.data_type = data_type
        self.attributes = attributes
        self.key = key
        self.value = value

    def to_json(self):

        json_data = {}
        if self.data_id:
            json_data["id"] = self.data_id

        if self.data_type:
            json_data["type"] = self.data_type

        if self.attributes:
            json_data["attributes"] = self.attributes

        return json_data

    def to_table(self):
        table = {"Name": self.key, "Value": self.value}
        return table


class ThreaIndicatorDetailsObject(BaseModel):

    def __init__(
        self,
        raw_data,
        ti_id=None,
        ti_type=None,
        attributes=None,
        ti_threat_level=None,
        ti_created_at=None,
        ti_updated_at=None,
        ti_threat_source=None,
        threat_type=None,
        threat_value=None,
    ):
        super(ThreaIndicatorDetailsObject, self).__init__(raw_data)
        self.ti_id = ti_id
        self.ti_type = ti_type
        self.attributes = attributes
        self.ti_threat_level = ti_threat_level
        self.ti_created_at = ti_created_at
        self.ti_updated_at = ti_updated_at
        self.ti_threat_source = ti_threat_source
        self.threat_type = threat_type
        self.threat_value = threat_value

    def to_json(self):

        json_data = {}
        if self.ti_id:
            json_data["id"] = self.ti_id

        if self.ti_type:
            json_data["type"] = self.ti_type

        if self.attributes:
            json_data["attributes"] = self.attributes

        return json_data

    def as_enrichment_data(self):
        enrichment_data = {
            "ti_id": self.ti_id,
            "ti_type": self.ti_type,
            "ti_threat_level": self.ti_threat_level,
            "ti_threat_source": self.ti_threat_source,
            "ti_created_at": self.ti_created_at,
            "ti_updated_at": self.ti_updated_at,
        }
        return add_prefix_to_dict(dict_to_flat(enrichment_data), CONFENSE_TRIAGE_PREFIX)

    def to_table(self):
        table = {
            "Threat ID": self.ti_id,
            "Threat Type": self.ti_type,
            "Threat Level": self.ti_threat_level,
            "Threat Source": self.ti_threat_source,
            "Threat Created At": self.ti_created_at,
            "Threat Updated At": self.ti_updated_at,
        }
        return table


class CategoriesObject(BaseModel):

    def __init__(self, raw_data, name, score, malicious, archived, category_id):
        super(CategoriesObject, self).__init__(raw_data)
        self.name = name
        self.score = score
        self.archived = archived
        self.malicious = malicious
        self.category_id = category_id

    def to_table(self):
        table = {
            "Name": self.name,
            "Score": self.score,
            "Malicious": self.malicious,
            "Archived": self.archived,
        }
        return table


class ReportObject(BaseModel):

    def __init__(self, raw_data, tags):
        super(ReportObject, self).__init__(raw_data)
        self.tags = tags


class Attachment(BaseModel):
    def __init__(
        self,
        raw_data,
        id,
        payload_id,
        type,
        attributes,
        filename,
        size,
        is_child,
        created_at,
        updated_at,
    ):
        super(Attachment, self).__init__(raw_data)
        self.id = id
        self.payload_id = payload_id
        self.type = type
        self.attributes = attributes
        self.filename = filename
        self.size = size
        self.is_child = is_child
        self.created_at = created_at
        self.updated_at = updated_at


class AttachmentPayload(BaseModel):
    def __init__(self, raw_data, id, mime_type, md5, sha256, risk_score):
        super(AttachmentPayload, self).__init__(raw_data)
        self.id = id
        self.mime_type = mime_type
        self.md5 = md5
        self.sha256 = sha256
        self.risk_score = risk_score


class Alert(BaseModel):
    def __init__(
        self,
        raw_data,
        id,
        location,
        risk_score,
        created_at,
        updated_at,
        urls,
        hostnames,
        threat_indicators,
        attachments,
        attachments_payloads,
        comments,
        headers,
    ):
        super(Alert, self).__init__(raw_data)
        self.id = id
        self.location = location
        self.name = f"Cofense Triage: {self.location} Report"
        self.uuid = uuid.uuid4()
        self.risk_score = risk_score
        self.created_at = convert_string_to_unix_time(created_at)
        self.updated_at = convert_string_to_unix_time(updated_at)
        self.urls = urls
        self.hostnames = hostnames
        self.threat_indicators = threat_indicators
        self.attachments = attachments
        self.attachments_payloads = attachments_payloads
        self.comments = comments
        self.headers = headers

    def get_alert_info(self, alert_info, environment_common, api_root):
        alert_info.environment = environment_common.get_environment(self.raw_data)
        alert_info.ticket_id = self.id
        alert_info.display_id = f"Cofense_{self.id}"
        alert_info.name = self.name
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = DEVICE_PRODUCT
        alert_info.priority = self.get_siemplify_priority()
        alert_info.rule_generator = self.location
        alert_info.start_time = self.created_at
        alert_info.end_time = self.created_at
        alert_info.events = self.create_events(api_root)

        return alert_info

    def get_siemplify_priority(self):
        result = 40

        if self.risk_score > 40:
            result = 60
        if self.risk_score > 60:
            result = 80
        if self.risk_score > 80:
            result = 100

        return result

    def create_events(self, api_root):
        self.raw_data["source_link"] = urljoin(api_root, f"reports/{self.id}")
        events = [dict_to_flat(self.raw_data)]

        events.extend(
            [
                self.get_related_entities_event(
                    url, url_event_name, url_event_description
                )
                for url in self.urls
            ]
        )
        events.extend(
            [
                self.get_related_entities_event(
                    hostname, hostname_event_name, hostname_event_description
                )
                for hostname in self.hostnames
            ]
        )
        events.extend(
            [
                self.get_related_entities_event(
                    threat_indicator,
                    threat_indicator_event_name,
                    threat_indicator_event_description,
                    {threat_indicator.threat_type: threat_indicator.threat_value},
                )
                for threat_indicator in self.threat_indicators
            ]
        )
        events.extend(
            [
                self.get_attachment_event(
                    attachment,
                    self.attachments_payloads,
                    attachment_event_name,
                    attachment_event_description,
                )
                for attachment in self.attachments
            ]
        )
        events.extend(
            [
                self.get_related_entities_event(
                    comment, comment_event_name, comment_event_description
                )
                for comment in self.comments
            ]
        )

        if self.headers:
            header_dict = {
                "event_name": header_event_name,
                "event_description": header_event_description,
                "creation_time": self.created_at
            }
            for header in self.headers:
                attributes = header.raw_data.get("attributes", {})
                header_dict[attributes.get("key")] = attributes.get("value")
            events.extend([dict_to_flat(header_dict)])

        return events

    def get_related_entities_event(
        self, data, event_name, event_description, additional_data={}
    ):
        data.raw_data["event_name"] = event_name
        data.raw_data["event_description"] = event_description
        data.raw_data["creation_time"] = self.created_at
        data.raw_data.get("attributes", {})["location"] = self.location
        data.raw_data.update(additional_data)

        return dict_to_flat(data.raw_data)

    def get_attachment_event(
        self, attachment, attachments_payloads, event_name, event_description
    ):
        payload = next(
            (
                attachments_payload
                for attachments_payload in attachments_payloads
                if attachments_payload.id == attachment.payload_id
            )
        )

        payload_attributes = (
            {
                "mime_type": payload.mime_type,
                "md5": payload.md5,
                "sha256": payload.sha256,
                "risk_score": payload.risk_score,
            }
            if payload
            else {}
        )
        attachment.attributes.update(payload_attributes)
        attachment.attributes["location"] = self.location

        return dict_to_flat(
            {
                "event_name": event_name,
                "event_description": event_description,
                "id": attachment.id,
                "payload_id": attachment.payload_id,
                "type": attachment.type,
                "attributes": attachment.attributes,
            }
        )


class RelatedReportObject(BaseModel):

    def __init__(self, raw_data, id, subject, created_at, location):
        super(RelatedReportObject, self).__init__(raw_data)
        self.id = id
        self.subject = subject
        self.created_at = created_at
        self.location = location

    def to_table(self):
        table = {
            "ID": self.id,
            "Subject": self.subject,
            "Created At": self.created_at,
            "Location": self.location,
        }
        return table


class Playbook(BaseModel):
    def __init__(
        self,
        raw_data: dict,
        name: str = None,
        active: bool = None,
        identifier: str = None,
        description: str = None,
        tags: list = None,
        created_at: str = None,
    ) -> None:
        super(Playbook, self).__init__(raw_data)
        self.raw_data = raw_data
        self.name = name
        self.active = active
        self.identifier = identifier
        self.description = description
        self.tags = convert_list_to_comma_string(tags)
        self.created_at = created_at

    def to_csv(self) -> dict:
        return {
            "Name": self.name,
            "Active": self.active,
            "ID": self.identifier,
            "Description": self.description,
            "Tags": self.tags,
            "Created At": self.created_at,
        }
