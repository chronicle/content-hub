from __future__ import annotations
import base64
import datetime
from typing import List, Dict, Optional

from .exceptions import TruSTARValidationException


def get_entity_summaries_dict(indicators_summary_list: List) -> Dict:
    """
    Create a dictionary of {identifier: [summaries]}
    :param indicators_summary_list: [IndicatorSummary] List of summaries
    :return: Dict[identifier, [IndicatorSummary]]
    """
    entity_summaries_dict = {}
    for indicator_summary in indicators_summary_list:
        if not entity_summaries_dict.get(indicator_summary.value):
            entity_summaries_dict[indicator_summary.value] = []
        entity_summaries_dict[indicator_summary.value].append(indicator_summary)

    return entity_summaries_dict


def get_max_indicator_severity(entity_summaries: List) -> Optional[int]:
    """
    Get the maximum indicator severity from all summaries
    :param entity_summaries: {[IndicatorSummary]} List of summaries
    :return: Max indicator severity
    """
    if not entity_summaries:
        return None

    severities = [summary.severity for summary in entity_summaries]
    return max(filter(None.__ne__, severities))


def timestamp_to_iso(timestamp: int) -> str:
    """
    Convert timestamp to iso-8601
    :param timestamp: {int} timestamp
    :return: Converted iso-8601 time. for example: 2021-04-10T10:31:36.988000
    """
    return datetime.datetime.utcfromtimestamp(timestamp / 1000).isoformat()


def convert_to_base64(to_convert: str) -> str:
    """
    convert string to base64 format
    :param to_convert: {str} The string to convert
    :return: Base64 string
    """
    return base64.b64encode(str.encode(to_convert)).decode()


def load_csv_to_list(csv: str, param_name: str) -> List[str]:
    """
    Load comma separated values represented as string to a list. Remove duplicates if exist
    :param csv: {str} of comma separated values with delimiter ','
    :param param_name: {str} the name of the parameter we are loading csv to list
    :return: {[str]} List of separated string values
            raise TruSTARValidationException if failed to parse csv string
    """
    try:
        return list(set([t.strip() for t in csv.split(",")]))
    except Exception:
        raise TruSTARValidationException(
            f'Failed to load comma separated string parameter "{param_name}"'
        )
