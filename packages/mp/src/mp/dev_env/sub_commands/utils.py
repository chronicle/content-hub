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

"""Helper utilities for developer environment subcommands."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import requests
import typer

from mp.dev_env import utils

if TYPE_CHECKING:
    from mp.core.custom_types import SingleJson
    from mp.dev_env.interfaces import DevEnvClient

logger: logging.Logger = logging.getLogger(__name__)


def get_backend_api_clean(config: SingleJson) -> DevEnvClient:
    """Initialize and authenticate the backend API client.

    Args:
        config: Environment configuration containing api_root and credentials.

    Returns:
        The authenticated DevEnvClient client.

    Raises:
        typer.Exit: If authentication fails.

    """
    try:
        return utils.get_backend_api(config)
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code in {401, 403}:
            target: str = str(config.get("api_root") or config.get("instance"))
            logger.error("=" * 80)  # ruff:ignore[error-instead-of-exception]
            logger.error(  # ruff:ignore[error-instead-of-exception]
                "[AUTHENTICATION ERROR] Unauthorized Access (Status Code %s)",
                e.response.status_code,
            )
            logger.error(  # ruff:ignore[error-instead-of-exception]
                "The credentials configured for '%s' are invalid or expired.",
                target,
            )
            msg: str = "Please update your credentials using: mp login"
            logger.error(msg)  # ruff:ignore[error-instead-of-exception]
            logger.error("=" * 80)  # ruff:ignore[error-instead-of-exception]
            raise typer.Exit(1) from None
        logger.error("Authentication failed: %s", e)  # ruff:ignore[error-instead-of-exception]
        raise typer.Exit(1) from None
    except typer.Exit:
        raise
    except Exception as e:  # ruff:ignore[blind-except]
        logger.error("Authentication failed: %s", e)  # ruff:ignore[error-instead-of-exception]
        raise typer.Exit(1) from None
