# Copyright 2025 Google LLC
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

"""exceptions
==========

A module containing all constant in use by TIPCommon package,
and common constant used in Marketplace Integrations

Usage Example::

    from TIPCommon.exceptions import ConnectorProcessingError

    raise ConnectorProcessingError("spam and eggs")
"""


# Connector Exceptions ####
class GeneralConnectorException(Exception):
    """General Connector Exception"""


class ConnectorValidationError(GeneralConnectorException):
    """Connector Validation Error"""


class ConnectorContextError(GeneralConnectorException):
    """Connector Context Error"""


class ConnectorSetupError(GeneralConnectorException):
    """Connector Initialization Error"""


class ConnectorProcessingError(GeneralConnectorException):
    """Connector Processing Error"""


# Action Exceptions ####
class GeneralActionException(Exception):
    """General Action Exception"""


class ActionSetupError(GeneralActionException):
    """ACTION Initialization Error"""


class CaseResultError(GeneralActionException):
    """Errors that happen when sending data to case result"""


class SDKWrapperError(GeneralActionException):
    """Errors that happen in SDK methods wrappers"""


class EnrichActionError(GeneralActionException):
    """Errors that happen in an enrichment action"""


# Job Exceptions ####
class GeneralJobException(Exception):
    """General Job Exception"""


class JobSetupError(GeneralActionException):
    """Job Initialization Error"""


class RefreshTokenRenewalJobException(GeneralJobException):
    """Failure in a RefreshTokenRenewalJob instance"""


# General Exceptions ####
class EmptyMandatoryValues(Exception):
    """Exception for empty mandatory values"""


class ParameterExtractionError(Exception):
    """Parameter extraction error"""


class InvalidTimeException(Exception):
    """Exception for invalid time"""


class ParameterValidationError(Exception):
    """Raised when a parameter is invalid."""

    def __init__(
        self,
        param_name,
        value,
        message,
        exception=None,
        print_value=True,
        print_error=False,
    ):
        msg = message
        if print_error and exception is not None:
            msg = f"{msg} - {exception}"

        super().__init__(
            f'Invalid parameter "{param_name}". {msg}.'
            + (f" Wrong value provided: {value}" if print_value else "")
        )


class InternalJSONDecoderError(Exception):
    """Internal Json parsing error using json.load/dump that requires only a msg"""


# GCP Exceptions ####
class GoogleCloudException(Exception):
    """General Google Cloud Exception"""


class AlreadyExistsError(GoogleCloudException):
    """GCP resource already exists"""


class NotFoundError(GoogleCloudException):
    """GCP resource not found"""


class BadGatewayError(GoogleCloudException):
    """A server between the client and the backend GCP servers
    detected a temporary issue
    """


class DeadlineExceededError(GoogleCloudException):
    """The request did not complete in the time allocated."""


class InvalidArgumentError(GoogleCloudException):
    """Invalid Request to GCP resource"""


class FailedPreconditionError(GoogleCloudException):
    """Failed precondition error for GCP request."""


class PermissionDeniedError(GoogleCloudException):
    """The client does not have permission to perform the operation
    on the resource
    """


class UnauthenticatedError(GoogleCloudException):
    """The client is not authenticated properly"""


class UnavailableError(GoogleCloudException):
    """The GCP service was unable to process a request."""


class ResourceExhaustedError(GoogleCloudException):
    """This error indicates that the quota for the cloud project has been
    exceeded, or that there are too many concurrent requests from the client
    """


class ImpersonationUnauthorizedError(GoogleCloudException):
    """The caller is not authorized to impersonate the service account"""


class OauthError(Exception):
    """Generic exception raised when an error occurs in Oauth flow"""


class SMIMEMailError(Exception):
    """Custom exception for S/MIME email processing errors."""


class NotSupportedPlatformVersion(Exception):
    """Custom exception for not supported platform version errors."""
