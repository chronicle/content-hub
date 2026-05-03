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
class FreshworksFreshserviceManagerError(Exception):
    """
    General Exception for Freshworks Freshservice manager
    """

    pass


class FreshworksFreshserviceAPILimitError(Exception):
    """
    API Limit Exception for Freshworks Freshservice manager
    """

    pass


class FreshworksFreshserviceTicketsConnectorError(Exception):
    """
    General Exception for Freshworks Freshservice Tickets connector
    """

    pass


class FreshworksFreshserviceValidationError(Exception):
    """
    Validation Exception for Freshworks Freshservice manager
    """

    pass


class FreshworksFreshserviceMissingAgentError(Exception):
    """
    Missing Agent Exception for Freshworks Freshservice manager
    """

    pass


class FreshworksFreshserviceMissingGroupAgentError(Exception):
    """
    Missing Agent Group Exception for Freshworks Freshservice manager
    """

    pass


class FreshworksFreshserviceAuthorizationError(Exception):
    """
    Authorization Exception for Freshworks Freshservice manager
    """

    pass


class FreshworksFreshserviceNotFoundError(Exception):
    """
    Not Found Exception for Freshworks Freshservice manager
    """

    pass


class FreshworksFreshserviceMissingRequesterError(Exception):
    """
    Missing Requester Exception for Freshworks Freshservice manager
    """

    pass


class FreshworksFreshserviceTicketsClosureJobError(Exception):
    """
    General Exception for Freshworks Freshservice Tickets Closure job
    """

    pass


class FreshworksFreshserviceTicketsConversationsJobError(Exception):
    """
    General Exception for Freshworks Freshservice Tickets Conversations job
    """

    pass


class FreshworksFreshserviceDuplicateValueError(Exception):
    """
    Duplicate value Exception for Freshworks Freshservice manager
    """

    pass


class FreshworksFreshserviceMethodNotAllowedError(Exception):
    """
    Method Not Allowed Exception for Freshworks Freshservice manager
    """

    pass


class FreshworksFreshserviceNegativeValueException(Exception):
    """
    Negative value Exception
    """

    pass


class FreshworksFreshserviceNonExistingFileError(Exception):
    """
    Non-existing file Exception
    """

    pass


class FreshworksFreshserviceSizeLimitError(Exception):
    """
    Over file size limit exception
    """

    pass
