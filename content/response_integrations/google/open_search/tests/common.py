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

import pathlib
from typing import Collection

from TIPCommon.types import SingleJson

from integration_testing.common import get_def_file_content

VALID_JSON_SUFFIXES: Collection[str] = (
    ".json",
    ".yaml",
    ".def",
    ".yaml",
    ".yaml",
)

INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent

CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
INVALID_CONFIG_PATH: pathlib.Path = (
    pathlib.Path(__file__).parent / "invalid_config.json"
)
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)
MOCK_DATA: pathlib.Path = pathlib.Path(__file__).parent / "mock_data.json"

SEARCH_RESULTS = {
    "timed_out": False,
    "_shards": {"total": 1, "successful": 1, "skipped": 0, "failed": 0},
    "hits": {
        "total": {"value": 1, "relation": "eq"},
        "max_score": 1.0,
        "hits": [
            {
                "_index": "test-index",
                "_id": "1",
                "_score": 1.0,
                "_source": {"foo": "bar"},
            }
        ],
    },
}


SUCCESS_INFO_RESPONSE = {
    "name": "mock-node-1",
    "cluster_name": "mock-cluster",
    "cluster_uuid": "_na_",
    "version": {
        "distribution": "opensearch",
        "number": "2.5.0",
        "build_type": "tar",
        "build_hash": "mock_hash",
        "build_date": "2023-01-24T21:33:49.847Z",
        "build_snapshot": False,
        "lucene_version": "9.4.2",
        "minimum_wire_compatibility_version": "7.10.0",
        "minimum_index_compatibility_version": "7.0.0",
    },
    "tagline": "The OpenSearch Project",
}

FAILURE_AUTH_RESPONSE = {"error": "Unauthorized"}
