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
from .datamodels import Process, FileHashMetadata, FileHashSummary, Event


class CBEnterpriseEDRParser:
    """
    CB Enterprise EDR Transformation Layer.
    """

    @staticmethod
    def build_siemplify_process_obj(process_data):
        return Process(raw_data=process_data, **process_data)

    @staticmethod
    def build_siemplify_event_obj(event_data):
        return Event(raw_data=event_data, **event_data)

    @staticmethod
    def build_siemplify_filehash_metadata_obj(filehash_metadata):
        return FileHashMetadata(raw_data=filehash_metadata, **filehash_metadata)

    @staticmethod
    def build_siemplify_filehash_summary_obj(filehash_summary):
        return FileHashSummary(raw_data=filehash_summary, **filehash_summary)
