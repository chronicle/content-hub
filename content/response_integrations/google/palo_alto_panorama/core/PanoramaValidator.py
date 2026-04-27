from __future__ import annotations
from .PanoramaExceptions import PanoramaSeverityException
from .PanoramaConstants import PANORAMA_TO_SIEM_SEVERITY
from .PanoramaCommon import PanoramaCommon


class PanoramaValidator:
    @staticmethod
    def validate_severity(severity):
        # type: (str or unicode) -> None or PanoramaSeverityException
        """
        Validate if severity is acceptable
        @param severity: Severity. Ex. Low
        """
        acceptable_severities = [
            key.lower() for key in list(PANORAMA_TO_SIEM_SEVERITY.keys())
        ]
        if severity not in acceptable_severities:
            raise PanoramaSeverityException(
                f'Severity "{severity}" is not in {PanoramaCommon.convert_list_to_comma_separated_string(acceptable_severities)}'
            )
