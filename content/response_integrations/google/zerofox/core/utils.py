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
from typing import ContextManager

import os
import mimetypes
from contextlib import contextmanager

from TIPCommon.extraction import extract_configuration_param
from TIPCommon.types import ChronicleSOAR, SingleJson
from ..core import constants
from ..core.datamodels import IntegrationParameters


def get_integration_parameters(siemplify: ChronicleSOAR) -> IntegrationParameters:
    """Get the parameters object for Zerofox's auth and api manager
    Args:
        siemplify (ChronicleSOAR): SiemplifyAction object.

    Returns:
        IntegrationParameters: IntegrationParameters object.
    """
    api_root: str = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
    )
    api_token: str = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=True,
        remove_whitespaces=False,
    )
    verify_ssl: bool = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
    )
    integration_params: IntegrationParameters = IntegrationParameters(
        api_root=api_root,
        api_token=api_token,
        verify_ssl=verify_ssl,
        siemplify_logger=siemplify.LOGGER,
    )

    return integration_params


@contextmanager
def build_evidence_payload(file_path: str) -> ContextManager[SingleJson]:
    """
    Context manager that builds a multipart/form-data `files` payload.

    Args:
        file_path (str): Path to the file.

    Yields:
        ContextManager[SingleJson]: Dictionary to pass to `requests.post(files=...)`.
    """
    mime_type, _ = mimetypes.guess_type(file_path)
    mime_type = mime_type or "application/octet-stream"

    with open(file_path, "rb") as f:
        yield {
            "file": (os.path.basename(file_path), f, mime_type),
            "attachment_type": (None, "evidence"),
        }
