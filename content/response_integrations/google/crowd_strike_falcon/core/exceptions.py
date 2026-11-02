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
class CrowdStrikeError(Exception):
    pass


class CrowdStrikeManagerError(CrowdStrikeError):
    pass


class CrowdStrikeStreamError(CrowdStrikeError):
    pass


class CrowdStrikeParameterError(CrowdStrikeError):
    pass


class CrowdStrikeTimeoutError(CrowdStrikeError):
    pass


class CrowdStrikeSessionCreatedError(CrowdStrikeError):
    pass


class CrowdStrikeFalconValidatorException(CrowdStrikeError):
    pass


class NotExistingFilenamesException(CrowdStrikeError):
    pass


class NoSuitableEntitiesException(CrowdStrikeError):
    pass


class FolderNotFoundException(CrowdStrikeError):
    pass


class CrowdStrikeNotFoundError(CrowdStrikeError):
    pass


class CrowdStrikeUnsupportedType(CrowdStrikeError):
    pass


class CrowdStrikeUnauthorisedError(CrowdStrikeError):
    pass


class CrowdStrikeBadRequestError(CrowdStrikeError):
    pass


class CrowdStrikeInvalidUserException(CrowdStrikeError):
    pass


class ODSDetectionLevelError(CrowdStrikeError):
    pass


class ODSInvalidFilePathError(CrowdStrikeError):
    pass


class InvalidCidError(CrowdStrikeError):
    """Raise if invalid customer id provided."""


class AlertNotFoundException(CrowdStrikeError):
    """Raises when Alert not found in Crowdstrike instance."""


class CommentLimitException(CrowdStrikeError):
    """Raises when comment length exceeds more than 1024 characters."""


class InvalidParameterError(Exception):
    """Invalid parameter error."""


class ExpiredJobIdError(Exception):
    """Raises when JobId is expired."""


class CrowdStrikeImproperlyConfiguredError(CrowdStrikeError):
    """Raise if a configuration or definition is incorrect."""
