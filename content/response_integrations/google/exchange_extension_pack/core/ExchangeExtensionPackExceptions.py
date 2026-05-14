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
class ExchangeExtensionPackException(Exception):
    """
    General exception for Exchange Extension Pack
    """

    pass


class ExchangeExtensionPackPowershellException(ExchangeExtensionPackException):
    """
    Powershell not installed exception
    """

    pass


class ExchangeExtensionPackGssntlmsspException(ExchangeExtensionPackException):
    """
    Gssntlmssp not installed exception
    """

    pass


class ExchangeExtensionPackIncompleteInfoException(ExchangeExtensionPackException):
    """
    Exception in case incomplete information
    """

    pass


class ExchangeExtensionPackNoResults(ExchangeExtensionPackException):
    """
    Exception in case of no results
    """

    pass


class ExchangeExtensionPackNotFound(ExchangeExtensionPackException):
    """
    Exception for not found case
    """

    pass


class ExchangeExtensionPackAlreadyExist(ExchangeExtensionPackException):
    """
    Exception for already exist case
    """

    pass


class ExchangeExtensionPackSessionError(ExchangeExtensionPackException):
    """
    Exception in case of failed powershell session creation
    """

    pass


class ExchangeExtensionPackInvalidQuery(ExchangeExtensionPackException):
    """
    Exception in case of invalid query
    """

    pass


class ExchangeExtensionPackIncompleteParametersException(
    ExchangeExtensionPackException
):
    """
    Exception in case of incomplete parameters
    """

    pass
