from __future__ import annotations
import copy
import html

from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from TIPCommon import dict_to_flat, add_prefix_to_dict
from .constants import (
    DEVICE_VENDOR,
    DEVICE_PRODUCT,
    SEVERITY_MAPPING,
    KEY_PREFIX,
    SCORE_MAPPING,
    SCORE_COLORS,
    FALLBACK_ALERT_NAME,
    SEVERITY_COLOR_MAPPER,
)


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_table(self):
        return dict_to_flat(self.to_json())

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Alert(BaseModel):
    def __init__(
        self,
        raw_data,
        alert_id,
        title,
        details,
        severity,
        created_at,
        asset_name,
        asset_type,
        type_string,
    ):
        super(Alert, self).__init__(raw_data)
        self.flat_raw_data = dict_to_flat(raw_data)
        self.alert_id = alert_id
        self.title = title
        self.details = details
        self.severity = severity
        self.created_at = created_at
        self.created_at_ms = convert_string_to_unix_time(self.created_at)
        self.type_string = type_string
        self.asset_name = asset_name or f"{self.title}-{self.alert_id}"
        self.asset_type = asset_type or f"{self.type_string}-{self.alert_id}"
        self.events = []

    def get_alert_info(self, alert_info, environment_common, device_product_field):
        alert_info.environment = environment_common.get_environment(self.raw_data)
        alert_info.ticket_id = self.alert_id
        alert_info.display_id = f"{KEY_PREFIX}_{self.alert_id}"
        alert_info.name = self.title or self.type_string or FALLBACK_ALERT_NAME
        alert_info.description = self.details
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = self.flat_raw_data.get(device_product_field) or DEVICE_PRODUCT
        alert_info.priority = self.get_siemplify_severity()
        alert_info.rule_generator = self.title or self.type_string or FALLBACK_ALERT_NAME
        alert_info.source_grouping_identifier = self.title
        alert_info.start_time = self.created_at_ms
        alert_info.end_time = self.created_at_ms
        alert_info.events = self.to_events()

        return alert_info

    def get_siemplify_severity(self):
        return SEVERITY_MAPPING.get(self.severity, -1)

    def set_events(self):
        event = copy.deepcopy(self.raw_data)
        event[self.asset_type] = self.asset_name
        self.events = [event]

    def to_events(self):
        return [dict_to_flat(event) for event in self.events]


class AlertComment(BaseModel):
    def __init__(self, raw_data):
        super(AlertComment, self).__init__(raw_data)


class Framework(BaseModel):
    def __init__(
        self,
        raw_data,
        display_name,
        description,
        avg_score_percent,
        test_results_fail,
        test_results_pass,
        active,
    ):
        super(Framework, self).__init__(raw_data)
        self.display_name = display_name
        self.description = description
        self.avg_score_percent = avg_score_percent
        self.test_results_fail = test_results_fail
        self.test_results_pass = test_results_pass
        self.active = active

    def to_table(self):
        return {
            "Name": self.display_name,
            "Description": self.description,
            "Score": self.avg_score_percent,
            "Failed": self.test_results_fail,
            "Passed": self.test_results_pass,
            "Active": self.active,
        }

    def to_insight(self):
        return (
            f"<h2><strong>"
            f"{self.display_name}. "
            f"Score: <span style='color: {self.get_score_color()}'>{self.avg_score_percent}%</span> "
            f"Passed: {self.test_results_pass} "
            f"Failed: {self.test_results_fail}"
            f"</strong></h2>"
        )

    def get_score_color(self):
        if 0 <= self.avg_score_percent < SCORE_MAPPING.get("info"):
            return SCORE_COLORS.get("info")
        elif SCORE_MAPPING.get("info") <= self.avg_score_percent < SCORE_MAPPING.get("low"):
            return SCORE_COLORS.get("low")
        elif SCORE_MAPPING.get("low") <= self.avg_score_percent < SCORE_MAPPING.get("medium"):
            return SCORE_COLORS.get("medium")
        elif SCORE_MAPPING.get("medium") <= self.avg_score_percent < SCORE_MAPPING.get("high"):
            return SCORE_COLORS.get("high")

        return ""


class ScanStatus(BaseModel):
    def __init__(self, raw_data, scan_id, status):
        super(ScanStatus, self).__init__(raw_data)
        self.scan_id = scan_id
        self.status = status


class CVE(BaseModel):
    def __init__(
        self,
        raw_data,
        cve_id=None,
        summary=None,
        fix_available=None,
        asset_name=None,
        labels=None,
        published=None,
        source_link=None,
        affected_packages=None,
        severity=None,
        **kwargs,
    ):
        super().__init__(raw_data)
        self.cve_id = cve_id
        self.summary = summary
        self.fix_available = fix_available
        self.asset_name = asset_name
        self.labels = labels
        self.published = published
        self.source_link = source_link
        self.affected_packages = affected_packages
        self.severity = severity
        self.flat_data = dict_to_flat(self.raw_data)

    def to_csv(self, count=None):
        return {
            "ID": self.cve_id,
            "Description": self.summary,
            "Fix Available": self.fix_available,
            "Affected Assets Count": count,
            "Labels": (", ".join(self.labels) if isinstance(self.labels, list) else self.labels),
            "Publish Date": self.published,
        }

    def to_insight(self, asset_names, severity):
        asset_names = html.escape(", ".join(asset_names)) if asset_names else "N/A"
        description = html.escape(self.summary) if self.summary else "N/A"
        fix_available = self.fix_available if self.fix_available is not None else "N/A"
        labels = (
            html.escape(", ".join(self.labels) if isinstance(self.labels, list) else self.labels)
            if self.labels
            else "N/A"
        )
        published = html.escape(self.published) if self.published else "N/A"
        severity = severity.capitalize()
        severity_color = SEVERITY_COLOR_MAPPER[severity.lower()]
        source_link = html.escape(self.source_link)
        insight_html = (
            f"<h2><strong> Severity:<span {severity_color}> {severity}</span><br /></strong></h2>"
        )
        insight_html += f"<p><strong>Description: </strong> {description} <br /><strong>Fix Available: </strong> {fix_available} <br />"
        insight_html += f"<strong>Affected Assets: </strong> {asset_names}<br /><strong>Labels: </strong> {labels} <br /><strong>Publish Date: </strong> {published} <br /></p>"
        insight_html += f"<p>For more details visit the following link: <a href='{source_link}' target='_blank'>{source_link}&nbsp;</a></p>"
        insight_html += f"<p>&nbsp;</p>"
        return insight_html


class Asset(BaseModel):
    def __init__(
        self,
        raw_data,
        asset_name=None,
        asset_type=None,
        account_name=None,
        asset_category=None,
        asset_subcategory=None,
        asset_state=None,
        state=None,
        **kwargs,
    ):
        super().__init__(raw_data)
        self.asset_name = asset_name
        self.asset_type = asset_type
        self.account_name = account_name
        self.asset_category = asset_category
        self.asset_subcategory = asset_subcategory
        self.asset_state = asset_state
        self.state = state or {}
        self.state_severity = self.state.get("severity", "N/A")
        self.state_created_at = self.state.get("created_at", "N/A")
        self.state_last_seen = self.state.get("last_seen", "N/A")

    def to_csv(self):
        return {
            "Name": self.asset_name,
            "Type": self.asset_type,
            "Account": self.account_name,
            "Category": self.asset_category,
            "Subcategory": self.asset_subcategory,
            "State": self.asset_state,
            "Severity": self.state_severity,
            "First Seen": self.state_created_at,
            "Last Seen": self.state_last_seen,
        }

    def to_insight(self, asset_link=None):
        insight_html = ""
        insight_html += "<h2><strong>"
        insight_html += (
            f"Severity:<span {SEVERITY_COLOR_MAPPER[self.state_severity.lower()] if self.state_severity.lower() in SEVERITY_COLOR_MAPPER.keys() else ''}> "
            f"{self.state_severity.capitalize() if self.state_severity.lower() in SEVERITY_COLOR_MAPPER.keys() else self.state_severity}</span> "
        )
        insight_html += "<br /></strong></h2>"
        insight_html += f"<p><strong>Name: </strong> {self.asset_name} <br>"
        insight_html += f"<strong>Type: </strong> {self.asset_type} <br>"
        insight_html += f"<strong>Account: </strong> {self.account_name} <br>"
        insight_html += f"<strong>Category: </strong> {self.asset_category} <br>"
        insight_html += f"<strong>Subcategory: </strong> {self.asset_subcategory} <br>"
        insight_html += f"<strong>State: </strong> {self.asset_state} <br>"
        insight_html += f"<strong>First Seen: </strong> {self.state_created_at} <br>"
        insight_html += f"<strong>Last Seen: </strong> {self.state_last_seen} <br>"
        insight_html += (
            f"<p>For more details visit the following link: <a href='{asset_link}' target='_blank'>"
            f"{asset_link}&nbsp;</a></p>"
        )
        insight_html += "<p>&nbsp;</p>"

        return insight_html
