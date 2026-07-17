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

import logging
import requests
import typer

from mp.dev_env import api

logger: logging.Logger = logging.getLogger(__name__)


def get_backend_api_clean(config: dict[str, str]) -> api.BackendAPI:
    """Initialize and authenticates the backend API client without logging tracebacks on failure.

    Args:
        config: Environment configuration containing api_root and credentials.

    Returns:
        The authenticated BackendAPI client.

    Raises:
        typer.Exit: If authentication fails.

    """
    try:
        if config.get("api_key"):
            backend_api = api.BackendAPI(api_root=config["api_root"], api_key=config["api_key"])
        else:
            backend_api = api.BackendAPI(
                api_root=config["api_root"],
                username=config["username"],
                password=config["password"],
            )

        backend_api.login()
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code in {401, 403}:
            logger.error("=" * 80)
            logger.error(
                "[AUTHENTICATION ERROR] Invalid API Key or Unauthorized Access (Status Code %s)",
                e.response.status_code,
            )
            logger.error(
                "The API key or credentials configured for '%s' are invalid or expired.",
                config.get("api_root"),
            )
            logger.error("Please update your credentials using: uv run --project packages/mp mp login")
            logger.error("=" * 80)
            raise typer.Exit(1) from None
        logger.error("Authentication failed: %s", e)  # noqa: TRY400
        raise typer.Exit(1) from None
    except Exception as e:  # noqa: BLE001
        logger.error("Authentication failed: %s", e)  # noqa: TRY400
        raise typer.Exit(1) from None
    else:
        return backend_api
