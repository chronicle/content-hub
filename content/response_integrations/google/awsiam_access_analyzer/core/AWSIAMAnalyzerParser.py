# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
