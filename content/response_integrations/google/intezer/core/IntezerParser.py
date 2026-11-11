from __future__ import annotations

from TIPCommon.types import SingleJson

from intezer.core.datamodels import (
    Detonate,
    Alert,
    SubmitAlert,
    URLReport,
    IndexFile,
    SubmitEmail,
    FileAnalysis,
    FileAnalysisResult,
    Ioc,
    Ttps,
    SubAnalysis,
    SubAnalysisMetaData,
    SubAnalysisCodeReuse,
    Id,
)


def build_detonate_object(
    raw_data: SingleJson,
    analysis_id: str,
    analysis_status: str,
    analysis_type: str,
    identifier: str,
) -> Detonate:
    """Builds detonate object

    Args:
        identifier: identifier of the detonate object
        analysis_type: analysis type of the detonate object
        analysis_status: status of the detonate object
        analysis_id: analysis id of the detonate object
        raw_data: Raw json from the response having information
        for detonate

    Returns:
        Detonate object
    """
    return Detonate(
        raw_data=raw_data,
        analysis_id=analysis_id,
        analysis_status=analysis_status,
        analysis_type=analysis_type,
        identifier=identifier,
    )


def build_get_alert_object(raw_data: SingleJson) -> Alert:
    """Builds alert object

    Args:
        raw_data: Raw json from the response having information
        for detonate

    Returns:
        Alert object
    """
    return Alert(raw_data=raw_data, status=raw_data["status"])


def build_submit_alert_object(raw_data: SingleJson) -> SubmitAlert:
    """Builds alert object

    Args:
        raw_data: Raw json from the response having information
        for detonate

    Returns:
        SubmitAlert object
    """
    return SubmitAlert(raw_data=raw_data, alert_id=raw_data.get("alert_id", ""))


def build_get_url_report_object(raw_data: SingleJson) -> URLReport:
    """Builds url report object

    Args:
        raw_data: Raw json from the response having information

    Returns:
        URLReport object
    """
    return URLReport(result_data=raw_data["result"], status=raw_data["status"])


def build_index_file_object(raw_data: SingleJson) -> IndexFile:
    """Builds index file object

    Args:
        raw_data: Raw json from the response having information
    Returns:
        An IndexFile object
    """
    return IndexFile(
        result_data=raw_data.get("result", {}), status=raw_data.get("status", "")
    )


def build_id_object(raw_data: SingleJson) -> Id:
    """Builds an Id object

    Args:
        raw_data: Raw json from the response having information
    Returns:
        An Id object
    """
    return Id(item_id=raw_data["result_url"].split("/")[-1])


def build_index_unset_file_object(raw_data: SingleJson, status: str) -> IndexFile:
    """Builds index unset file object

    Args:
        status: api response status
        raw_data: Raw json from the response having information
            for detonate
    Returns:
        IndexFile object
    """
    return IndexFile(result_data=raw_data, status=status)


def build_submit_email_object(raw_data: SingleJson) -> SubmitEmail:
    """Builds alert object

    Args:
        raw_data: Raw json from the response having information
        for Suspicious email
    Returns:
        Submit email object
    """
    return SubmitEmail(raw_data=raw_data, alert_id=raw_data["alert_id"])


def build_file_analysis_object(status: str, analysis: dict) -> FileAnalysis:
    """Builds file analysis object

    Args:
        status: Status of the analysis of the file
        analysis: Full analysis details
    Returns:
        FileAnalysis object
    """
    return FileAnalysis(status=status, analysis=analysis)


def build_file_analysis_result_object(raw_data: SingleJson) -> FileAnalysisResult:
    """Builds file analysis object

    Args:
        raw_data: Raw json from the response having information
    Returns:
        FileAnalysis object
    """
    return FileAnalysisResult(
        result_data=raw_data.get("result", {}),
        analysis_id=raw_data.get("result", {}).get("analysis_id", ""),
        status=raw_data.get("status", ""),
    )


def build_iocs_object(raw_data: SingleJson) -> Ioc:
    """Builds ioc object

    Args:
        raw_data: Raw json from the response having information
    Returns:
        An Ioc object
    """
    return Ioc(raw_data=raw_data["result"])


def build_ttps_object(raw_data: SingleJson) -> Ttps:
    """Builds ttps object

    Args:
        raw_data: Raw json from the response having information
    Returns:
        A Ttps object
    """
    return Ttps(raw_data=raw_data["result"])


def build_sub_analyses_object(raw_data: SingleJson) -> SubAnalysis:
    """Builds sub analysis object

    Args:
        raw_data: Raw json from the response having information
    Returns:
        A sub analysis object
    """
    sub_analysis_id = ""
    for sub_analysis in raw_data["sub_analyses"]:
        if sub_analysis.get("source") == "root":
            sub_analysis_id = sub_analysis.get("sub_analysis_id", "")
    return SubAnalysis(sub_analysis_id=sub_analysis_id)


def build_sub_analysis_metadata_object(raw_data: SingleJson) -> SubAnalysisMetaData:
    """Builds sub analysis object

    Args:
        raw_data: Raw json from the response having information
    Returns:
        A sub analysis metadata object
    """
    return SubAnalysisMetaData(raw_data=raw_data)


def build_sub_analysis_code_reuse_object(raw_data: SingleJson) -> SubAnalysisCodeReuse:
    """Builds sub analysis object

    Args:
        raw_data: Raw json from the response having information
    Returns:
        A sub analysis code reuse object
    """
    return SubAnalysisCodeReuse(raw_data=raw_data)
