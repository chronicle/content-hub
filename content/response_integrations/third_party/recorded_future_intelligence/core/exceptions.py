############################## TERMS OF USE ################################### # noqa: E266
# The following code is provided for demonstration purposes only, and should  #
# not be used without independent verification. Recorded Future makes no      #
# representations or warranties, express, implied, statutory, or otherwise,   #
# regarding this code, and provides it strictly "as-is".                      #
# Recorded Future shall not be liable for, and you assume all risk of         #
# using the foregoing.                                                        #
###############################################################################

# ============================================================================#
# title           :exceptions.py                                    noqa: ERA001
# description     :This Module contains the Exceptions raised from Recorded Future API
# author          :support@recordedfuture.com                       noqa: ERA001
# date            :10-31-2025
# python_version  :3.11                                             noqa: ERA001
# product_version :8.0
# ============================================================================#

from __future__ import annotations


class RecordedFutureDataModelTransformationLayerError(Exception):
    """General Exception for RecordedFuture DataModelTransformation."""


class RecordedFutureInvalidCaseTypeError(Exception):
    """Exception when trying to perform an action on a case where it isn't valid."""


class RecordedFutureCommonError(Exception):
    """General Exception for RecordedFuture Common."""


class RecordedFutureManagerError(Exception):
    """General Exception for RecordedFuture manager."""


class RecordedFutureNotFoundError(Exception):
    """Exception for not found items."""


class RecordedFutureUnauthorizedError(Exception):
    """Exception for Unauthorized case."""


class SandboxTimeoutError(Exception):
    """Exception for Recorded Future Sandbox Timeout."""
