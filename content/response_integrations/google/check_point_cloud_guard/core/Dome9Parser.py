from __future__ import annotations
from .datamodels import Finding


class Dome9Parser:
    """
    Dome9 Transformation Layer.
    """

    @staticmethod
    def build_siemplify_finding_obj(finding_data):
        return Finding(raw_data=finding_data, **finding_data)
