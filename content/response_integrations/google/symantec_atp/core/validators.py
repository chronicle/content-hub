from __future__ import annotations
from .constants import PRIORITIES
from TIPCommon import convert_list_to_comma_string


class SymantecATPValidatorException(Exception):
    pass


class SymantecATPValidator:
    @staticmethod
    def validate_priorities(priorities):
        for priority in priorities:
            if not priority.upper() in PRIORITIES:
                raise SymantecATPValidatorException(
                    f"{priority} not in {convert_list_to_comma_string(PRIORITIES)}"
                )
