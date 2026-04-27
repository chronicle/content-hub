from __future__ import annotations
from typing import List, Dict

from .datamodels import (
    Enclave,
    RelatedIndicator,
    IndicatorMetadata,
    IndicatorSummaryResponse,
    IndicatorSummary,
    RelatedReport,
    ReportDetails,
    ReportTag,
)


class TruSTARTransformationLayer:
    """
    TruSTAR Transformation Layer
    """

    @staticmethod
    def build_enclaves_obj_list(raw_response: List) -> List[Enclave]:
        return [
            TruSTARTransformationLayer.build_enclave_obj(raw_enclave)
            for raw_enclave in raw_response
        ]

    @staticmethod
    def build_enclave_obj(raw_enclave: Dict) -> Enclave:
        return Enclave(
            raw_data=raw_enclave,
            id=raw_enclave.get("id"),
            type=raw_enclave.get("type"),
            name=raw_enclave.get("name"),
            workflow_supported=raw_enclave.get("workflowSupported"),
            template_name=raw_enclave.get("templateName"),
            read=raw_enclave.get("read"),
            create=raw_enclave.get("create"),
            update=raw_enclave.get("update"),
        )

    @staticmethod
    def build_related_indicator_obj_list(raw_response: Dict) -> List[RelatedIndicator]:
        return [
            TruSTARTransformationLayer.build_related_indicator_obj(raw_indicator)
            for raw_indicator in raw_response.get("items", [])
        ]

    @staticmethod
    def build_related_indicator_obj(raw_indicator: Dict):
        return RelatedIndicator(
            raw_data=raw_indicator,
            indicator_type=raw_indicator.get("indicatorType"),
            value=raw_indicator.get("value"),
            guid=raw_indicator.get("guid"),
        )

    @staticmethod
    def build_indicator_meta_objects(response) -> List[IndicatorMetadata]:
        indicator_meta_raw_data = response.json()
        return [
            TruSTARTransformationLayer.build_indicator_meta_object(indicator_meta)
            for indicator_meta in indicator_meta_raw_data
        ]

    @staticmethod
    def build_indicator_meta_object(indicator_meta_raw_data) -> IndicatorMetadata:
        return IndicatorMetadata(
            raw_data=indicator_meta_raw_data, **indicator_meta_raw_data
        )

    @staticmethod
    def build_indicator_summary_response(response) -> IndicatorSummaryResponse:
        response_raw_data = response.json()
        summaries = TruSTARTransformationLayer.build_indicator_summary_objects(
            response_raw_data.get("items", [])
        )
        return IndicatorSummaryResponse(
            raw_data=response_raw_data, summary_items=summaries, **response_raw_data
        )

    @staticmethod
    def build_indicator_summary_objects(items) -> List[IndicatorSummary]:
        return [
            TruSTARTransformationLayer.build_indicator_summary_object(summary)
            for summary in items
        ]

    @staticmethod
    def build_indicator_summary_object(summary_raw_data) -> IndicatorSummary:
        return IndicatorSummary(raw_data=summary_raw_data, **summary_raw_data)

    @staticmethod
    def build_related_report_obj_list(raw_response: Dict) -> List[RelatedReport]:
        return [
            TruSTARTransformationLayer.build_report_obj(raw_report)
            for raw_report in raw_response.get("items", [])
        ]

    @staticmethod
    def build_report_obj(raw_report):
        return RelatedReport(
            raw_data=raw_report,
            id=raw_report.get("id"),
            created=raw_report.get("created"),
            updated=raw_report.get("updated"),
            distribution_type=raw_report.get("distributionType"),
            time_began=raw_report.get("timeBegan"),
            enclave_ids=raw_report.get("enclaveIds", []) or [],
        )

    @staticmethod
    def build_report_details_obj(raw_report) -> ReportDetails:
        return ReportDetails(
            raw_data=raw_report,
            id=raw_report.get("id"),
            created=raw_report.get("created"),
            updated=raw_report.get("updated"),
            title=raw_report.get("title"),
            distribution_type=raw_report.get("distributionType"),
            submission_status=raw_report.get("submissionStatus"),
            time_began=raw_report.get("timeBegan"),
            report_body=raw_report.get("reportBody"),
            external_tracking_id=raw_report.get("externalTrackingId"),
            enclave_ids=raw_report.get("enclaveIds", []) or [],
        )

    @staticmethod
    def build_report_tags_obj_list(raw_response: List) -> List[ReportTag]:
        return [
            TruSTARTransformationLayer.build_report_tag_obj(raw_report_tag)
            for raw_report_tag in raw_response
        ]

    @staticmethod
    def build_report_tag_obj(raw_report_tag) -> ReportTag:
        return ReportTag(
            raw_data=raw_report_tag,
            guid=raw_report_tag.get("guid"),
            name=raw_report_tag.get("name"),
            enclave_id=raw_report_tag.get("enclaveId"),
        )
