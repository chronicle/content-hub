from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


class BaseModel:
    """Base model for all Cyware datamodels."""

    def __init__(self, raw_data: Dict[str, Any]):
        self.raw_data = raw_data

    def to_json(self) -> Dict[str, Any]:
        """Return raw data as JSON."""
        return self.raw_data

    @staticmethod
    def _stringify(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value)
        except TypeError:
            return str(value)


class AllowedIOC(BaseModel):
    """Model for Allowed IOC."""

    def __init__(self, raw_data: Dict[str, Any]):
        super().__init__(raw_data)
        self.id = raw_data.get("id", "N/A")
        self.type = raw_data.get("type", "N/A")
        self.value = raw_data.get("value", "N/A")

    def to_csv(self) -> Dict[str, Any]:
        """Return data formatted for CSV/table output."""
        return {
            "ID": self.id,
            "Type": self.type,
            "Value": self.value,
        }


class IOCDetails(BaseModel):
    """Model for IOC Details."""

    def __init__(self, raw_data: Dict[str, Any]):
        super().__init__(raw_data)
        self.id = raw_data.get("id", "N/A")
        self.name = raw_data.get("name", "N/A")
        self.ioc_type = raw_data.get("ioc_type", "N/A")
        self.analyst_score = raw_data.get("analyst_score", "N/A")
        self.confidence_score = raw_data.get("confidence_score", "N/A")
        self.tlp = raw_data.get("tlp", "N/A")
        self.created = raw_data.get("created", "N/A")
        self.modified = raw_data.get("modified", "N/A")
        self.tags = raw_data.get("tags", [])
        self.sources = raw_data.get("sources", [])
        self.is_whitelisted = raw_data.get("is_whitelisted", False)
        self.is_false_positive = raw_data.get("is_false_positive", False)
        self.is_deprecated = raw_data.get("is_deprecated", False)
        self.is_reviewed = raw_data.get("is_reviewed", False)
        self.manual_review = raw_data.get("manual_review", False)

    def to_csv(self) -> Dict[str, Any]:
        """Return data formatted for CSV/table output."""
        tags_str = "|".join(self.tags) if self.tags else "N/A"
        sources_str = (
            "|".join(s.get("name", "N/A") for s in self.sources if s.get("name", ""))
            if self.sources
            else "N/A"
        )

        return {
            "ID": self.id,
            "IOC Value": self.name if self.name else "N/A",
            "IOC Type": self.ioc_type if self.ioc_type else "N/A",
            "Analyst Score": self.analyst_score,
            "Confidence Score": self.confidence_score,
            "TLP": self.tlp if self.tlp else "N/A",
            "Tags": tags_str,
            "Sources": sources_str,
            "Is Whitelisted": "Yes" if self.is_whitelisted else "No",
            "Is False Positive": "Yes" if self.is_false_positive else "No",
        }

    def enrich_data(self) -> Dict[str, Any]:
        """
        Get enrich data for siemplify entity.
        Returns:
            dict: Key of IOC with Cyware_ prefix
        """
        enrichment: Dict[str, Any] = {}

        field_mapping = {
            "analyst_score": ("Cyware_analyst_score", self.analyst_score),
            "confidence_score": ("Cyware_confidence_score", self.confidence_score),
            "is_whitelisted": ("Cyware_is_whitelisted", self.is_whitelisted),
            "is_false_positive": ("Cyware_is_false_positive", self.is_false_positive),
            "is_deprecated": ("Cyware_is_deprecated", self.is_deprecated),
            "is_reviewed": ("Cyware_is_reviewed", self.is_reviewed),
            "manual_review": ("Cyware_manual_review", self.manual_review),
            "tlp": ("Cyware_tlp", self.tlp),
        }

        for raw_key, (enrichment_key, value) in field_mapping.items():
            if raw_key not in self.raw_data:
                continue

            if isinstance(value, str):
                if value.strip():
                    enrichment[enrichment_key] = value
            elif value is not None:
                enrichment[enrichment_key] = value

        return enrichment


class QuickIntelStatus(BaseModel):
    """Model representing quick intel creation + status."""

    def __init__(
        self,
        creation_response: Optional[Dict[str, Any]] = None,
        status_response: Optional[Dict[str, Any]] = None,
    ):
        super().__init__({
            "creation_response": creation_response or {},
            "status_response": status_response or {},
        })
        creation_data = creation_response or {}
        status_data = status_response or {}
        self.details = creation_data.get("details")
        self.task_id = creation_data.get("task_id")
        self.report_id = status_data.get("report_id")
        self.report_status = status_data.get("report_status")
        self.message = status_data.get("message")

    def to_csv(self) -> List[Dict[str, Any]]:
        return [
            {
                "Details": self._stringify(self.details) or "N/A",
                "Task ID": self.task_id or "N/A",
                "Report ID": self.report_id or "N/A",
                "Report Status": self.report_status or "N/A",
                "Message": self._stringify(self.message) or "N/A",
            }
        ]


class FalsePositiveResult(BaseModel):
    """Model for Mark IOCs False Positive action."""

    def __init__(
        self,
        object_type: str,
        indicator_records: Optional[List[Dict[str, Any]]] = None,
        message: Optional[str] = None,
    ):
        super().__init__({
            "object_type": object_type,
            "indicator_records": indicator_records or [],
            "message": message,
        })
        self.object_type = object_type
        self.indicator_records = indicator_records or []
        self.message = message or "Processed"

    def to_csv(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for record in self.indicator_records:
            rows.append({
                "Object Type": self.object_type,
                "IOC Value": record.get("value", "N/A"),
                "Object ID": record.get("id", "N/A"),
                "Status": self.message,
            })

        if not rows:
            rows.append({
                "Object Type": self.object_type,
                "IOC Value": "N/A",
                "Object ID": "N/A",
                "Status": self.message,
            })

        return rows
