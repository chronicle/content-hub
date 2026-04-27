from __future__ import annotations
from .datamodels import Analyzer, Resource, Finding


class AWSIAMAnalyzerParser:
    """
    AWS IAM Analyzer Transformation Layer.
    """

    @staticmethod
    def build_analyzer_obj(raw_data):
        analyzer_data = raw_data.get("analyzer")
        return Analyzer(**analyzer_data)

    @staticmethod
    def build_resource_obj(raw_data):
        return Resource(**raw_data.get("resource"))

    @staticmethod
    def build_finding_objs(findings):
        return [AWSIAMAnalyzerParser.build_finding_obj(finding) for finding in findings]

    @staticmethod
    def build_finding_obj(object_data):
        raw_data = object_data
        return Finding(raw_data, **object_data)
