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
class PaloAltoPrismaCloudError(Exception):
    """General Exception for Palo Alto Prisma Cloud"""


class MaximumRequestLimitError(PaloAltoPrismaCloudError):
    """Maximum requests sent in a given amount of time"""


class InvalidAssetIDException(PaloAltoPrismaCloudError):
    """Exception in case of invalid AssetID"""


class InvalidEnrichAssetExecutionException(PaloAltoPrismaCloudError):
    """Exception in case of invalid EnrichAssetExecution"""


class InvalidParameterException(PaloAltoPrismaCloudError):
    """Exception in case of invalid attachment path"""


class InvalidAPIException(PaloAltoPrismaCloudError):
    """Exception in case of 400 status code"""
