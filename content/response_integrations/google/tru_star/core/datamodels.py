from __future__ import annotations
from typing import Optional, List, Dict

from TIPCommon import dict_to_flat, add_prefix_to_dict

from soar_sdk.SiemplifyUtils import convert_unixtime_to_datetime
from .consts import (
    INTEGRATION_PREFIX,
    COLORS_SECURITY_LEVEL_MAPPING,
    REVERES_SECURITY_LEVEL_MAPPING,
    REPORT_LINK,
    REPORT_BASE_URL,
    HTML_LINK,
    DATE_FORMAT,
)
from .utils import timestamp_to_iso, convert_to_base64


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def as_json(self):
        return self.raw_data

    def as_csv(self):
        return dict_to_flat(self.as_json())

    def as_flat(self):
        return dict_to_flat(self.raw_data)

    def as_enrichment(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Enclave(BaseModel):
    """
    Enclave data model
    """

    def __init__(
        self,
        raw_data,
        id: Optional[str] = None,
        type: Optional[str] = None,
        name: Optional[str] = None,
        template_name: Optional[str] = None,
        workflow_supported: Optional[str] = None,
        read: Optional[bool] = None,
        create: Optional[bool] = None,
        update: Optional[bool] = None,
    ):
        super(Enclave, self).__init__(raw_data)
        self.id: Optional[str] = id
        self.type: Optional[str] = type
        self.name: Optional[str] = name
        self.template_name: Optional[str] = template_name
        self.workflow_supported: Optional[str] = workflow_supported
        self.read: Optional[bool] = read
        self.create: Optional[bool] = create
        self.update: Optional[bool] = update

    def as_csv(self):
        return {
            "Name": self.name,
            "Read": self.read,
            "Create": self.create,
            "Update": self.update,
            "ID": self.id,
            "Type": self.type,
        }


class RelatedIndicator(BaseModel):
    """
    Related indicator data model
    """

    def __init__(
        self,
        raw_data,
        indicator_type: Optional[str] = None,
        value: Optional[str] = None,
        guid: Optional[str] = None,
    ):
        super(RelatedIndicator, self).__init__(raw_data)
        self.indicator_type: Optional[str] = indicator_type
        self.value: Optional[str] = value
        self.guid: Optional[str] = guid


class IndicatorMetadata:
    def __init__(
        self,
        raw_data,
        indicatorType: str = None,
        value: str = None,
        correlationCount: int = None,
        priorityLevel: str = None,
        noteCount: int = None,
        sightings: int = None,
        firstSeen: int = None,
        lastSeen: int = None,
        enclaveIds: List[str] = None,
        tags: List = None,
        source: str = None,
        notes: List = None,
        guid: str = None,
        **kwargs,
    ):
        self.raw_data = raw_data
        self.indicator_type = indicatorType
        self.value = value
        self.correlation_count = correlationCount
        self.priority_level = priorityLevel
        self.note_count = noteCount
        self.sightings = sightings
        self.first_seen = timestamp_to_iso(firstSeen)
        self.last_seen = timestamp_to_iso(lastSeen)
        self.enclave_ids = enclaveIds
        self.tags = tags
        self.source = source
        self.notes = notes
        self.guid = guid

    def as_json(self, summaries_json: List):
        self.raw_data["summaries"] = summaries_json
        return self.raw_data

    def as_enrichment(self, severity: int, prefix: str = INTEGRATION_PREFIX):
        data = {
            "sightings": self.sightings,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "tags": ", ".join([tag.get("name", "") for tag in self.tags]),
            "source": self.source,
            "security_level": severity or "N/A",
            "report_link": REPORT_LINK.format(convert_to_base64(self.guid)),
        }

        flat_data = dict_to_flat(data)
        return add_prefix_to_dict(flat_data, prefix) if prefix else data

    def as_csv(self, severity: int):
        return {
            "sightings": self.sightings,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "tags": ", ".join([tag.get("name", "") for tag in self.tags]),
            "source": self.source,
            "security_level": severity or "N/A",
            "report_link": REPORT_LINK.format(convert_to_base64(self.guid)),
        }

    def as_insight(self, severity):
        color_severity_str = (
            """<td><strong><span style="font-size: 17px";>&nbsp;N/A</span>"""
            if not severity
            else f"""<td><strong><span style="color:{COLORS_SECURITY_LEVEL_MAPPING.get(severity)}; font-size: 17px;"> &nbsp; {REVERES_SECURITY_LEVEL_MAPPING.get(severity)}</span><span style="color: #000000;"></span>"""
        )
        return f"""
        <table>
        <tbody>
        <tr>
        <td><strong><span style="font-size: 17px;">Severity:</span></strong></td>
        {color_severity_str}</span></strong></td>
        </tr>
        </tbody>
        </table>
        """


class IndicatorSummaryResponse:
    def __init__(
        self,
        raw_data,
        summary_items,
        pageNumber: int = None,
        totalPages: int = None,
        hasNext: bool = None,
        **kwargs,
    ):
        self.raw_data = raw_data
        self.summaries = summary_items
        self.page_number = pageNumber
        self.total_pages = totalPages
        self.hasNext = hasNext


class IndicatorSummary:
    def __init__(
        self,
        raw_data,
        reportId: str = None,
        updated: int = None,
        enclaveId: str = None,
        source: Dict[str, str] = None,
        severityLevel: int = None,
        type: str = None,
        value: str = None,
        score: Dict[str, str] = None,
        attributes: List[Dict] = None,
        **kwargs,
    ):
        self.raw_data = raw_data
        self.report_id = reportId
        self.updated = updated
        self.enclave_id = enclaveId
        self.source = source
        self.type = type
        self.value = value
        self.score = score
        self.attributes = attributes
        self.severity = severityLevel

    def as_json(self):
        return self.raw_data


class RelatedReport(BaseModel):
    """
    Related report data model
    """

    def __init__(
        self,
        raw_data,
        id: Optional[str] = None,
        created: Optional[int] = None,
        updated: Optional[int] = None,
        title: Optional[str] = None,
        distribution_type: Optional[str] = None,
        time_began: Optional[int] = None,
        enclave_ids: Optional[List[str]] = None,
    ):
        super(RelatedReport, self).__init__(raw_data)
        self.id = id
        self.created = created
        self.updated = updated
        self.title = title
        self.distribution_type = distribution_type
        self.time_began = time_began
        self.enclave_ids = enclave_ids or []


class ReportDetails(BaseModel):
    """
    Report details data model
    """

    def __init__(
        self,
        raw_data,
        id: Optional[str] = None,
        created: Optional[int] = None,
        updated: Optional[int] = None,
        title: Optional[str] = None,
        distribution_type: Optional[str] = None,
        time_began: Optional[int] = None,
        enclave_ids: Optional[List[str]] = None,
        submission_status: Optional[str] = None,
        report_body: Optional[str] = None,
        external_tracking_id: Optional[str] = None,
    ):
        super(ReportDetails, self).__init__(raw_data)
        self.id = id
        self.created = created
        self.updated = updated
        self.title = title
        self.distribution_type = distribution_type
        self.time_began = time_began
        self.submission_status = submission_status
        self.report_body = report_body
        self.external_tracking_id = external_tracking_id
        self.enclave_ids = enclave_ids or []

        try:
            self.created_date_formatted = convert_unixtime_to_datetime(
                self.created
            ).strftime(DATE_FORMAT)
        except:
            self.created_date_formatted = self.created

        try:
            self.updated_date_formatted = convert_unixtime_to_datetime(
                self.updated
            ).strftime(DATE_FORMAT)
        except:
            self.updated_date_formatted = self.updated

    @property
    def report_body_as_insight(self):
        return self.report_body.replace("\n", "<br>")

    @property
    def report_link(self):
        return REPORT_BASE_URL.format(report_id=self.id)

    @property
    def html_report_link(self):
        return HTML_LINK.format(link=self.report_link)


class ReportTag(BaseModel):
    """
    Report tag data model
    """

    def __init__(
        self,
        raw_data,
        guid: Optional[str] = None,
        name: Optional[str] = None,
        enclave_id: Optional[str] = None,
    ):
        super(ReportTag, self).__init__(raw_data)
        self.guid = guid
        self.name = name
        self.enclave_id = enclave_id
