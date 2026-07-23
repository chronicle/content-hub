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
from __future__ import annotations

import json
import logging
from typing import Annotated, NamedTuple

import typer

from mp.dev_env import utils
from mp.telemetry import track_command

logger: logging.Logger = logging.getLogger(__name__)


login_app: typer.Typer = typer.Typer()


class DevEnvParams(NamedTuple):
    api_root: str | None
    auth_mode: str
    username: str | None
    password: str | None
    api_key: str | None
    project: str | None
    location: str | None
    instance: str | None
    credentials_file: str | None


def _gather_gcp_params(
    project: str | None,
    location: str | None,
    instance: str | None,
    credentials_file: str | None,
) -> DevEnvParams:
    """Prompt for any missing GCP fields and build the GCP-mode login params.

    Args:
        project: GCP project ID (prompted if None).
        location: Chronicle region (prompted if None).
        instance: Chronicle instance UUID (prompted if None).
        credentials_file: Optional path to a GCP credentials JSON file.

    Returns:
        The assembled GCP-mode login params.

    """
    if project is None:
        project = typer.prompt("GCP project ID")
    if location is None:
        location = typer.prompt("Chronicle region (e.g. us, europe)")
    if instance is None:
        instance = typer.prompt("Chronicle instance UUID")
    return DevEnvParams(
        api_root=None,
        auth_mode="gcp",
        username=None,
        password=None,
        api_key=None,
        project=project,
        location=location,
        instance=instance,
        credentials_file=credentials_file,
    )


def _gather_legacy_params(
    api_root: str | None,
    username: str | None,
    password: str | None,
    api_key: str | None,
) -> DevEnvParams:
    """Prompt for any missing legacy SOAR fields and build the legacy-mode login params.

    Args:
        api_root: The SOAR API root (prompted if None).
        username: Username for user/pass auth (prompted if needed).
        password: Password for user/pass auth (prompted if needed).
        api_key: API key for api-key auth.

    Returns:
        The assembled legacy-mode login params.

    """
    if api_root is None:
        api_root = typer.prompt("API root (e.g. https://playground.example.com)")
    if api_key is not None:
        auth_mode = "api_key"
        username = password = None
    else:
        auth_mode = "user_pass"
        if username is None:
            username = typer.prompt("Username")
        if password is None:
            password = typer.prompt("Password", hide_input=True)
    return DevEnvParams(
        api_root=api_root,
        auth_mode=auth_mode,
        username=username,
        password=password,
        api_key=api_key,
        project=None,
        location=None,
        instance=None,
        credentials_file=None,
    )


@login_app.command(name="login", help="Login to the development environment (playground).")
@track_command
def login(  # noqa: PLR0913, PLR0917
    api_root: Annotated[str | None, typer.Option(help="API root URL (legacy SOAR auth).")] = None,
    username: Annotated[str | None, typer.Option(help="Authentication username (legacy SOAR auth).")] = None,
    password: Annotated[
        str | None,
        typer.Option(help="Authentication password (legacy SOAR auth).", hide_input=True),
    ] = None,
    api_key: Annotated[
        str | None,
        typer.Option(help="Authentication API key (legacy SOAR auth).", hide_input=True),
    ] = None,
    project: Annotated[str | None, typer.Option(help="GCP project ID (--gcp mode).")] = None,
    location: Annotated[str | None, typer.Option(help="Chronicle region, e.g. 'us' (--gcp mode).")] = None,
    instance: Annotated[str | None, typer.Option(help="Chronicle instance UUID (--gcp mode).")] = None,
    credentials_file: Annotated[
        str | None,
        typer.Option(help="Path to a GCP credentials JSON file (--gcp mode, optional; defaults to ADC)."),
    ] = None,
    *,
    gcp: Annotated[
        bool,
        typer.Option("--gcp/--no-gcp", help="Authenticate to the Chronicle API using GCP credentials (ADC)."),
    ] = False,
    no_verify: Annotated[bool, typer.Option(help="Skip verification after saving.")] = False,
) -> None:
    """Authenticate to the dev environment (playground).

    Supports the legacy Siemplify SOAR auth (API key or username/password against an
    ``api_root``) and, with ``--gcp``, the Chronicle API using Application Default
    Credentials (identified by GCP project + Chronicle region + instance UUID).

    Args:
        api_root: The API root of the dev environment (legacy modes).
        username: The username to authenticate with (legacy user/pass mode).
        password: The password to authenticate with (legacy user/pass mode).
        api_key: The API key for authentication (legacy api-key mode).
        project: GCP project ID (gcp mode).
        location: Chronicle region, e.g. 'us' (gcp mode).
        instance: Chronicle instance UUID (gcp mode).
        credentials_file: Optional path to a GCP credentials JSON file (gcp mode).
        gcp: Use GCP Application Default Credentials against the Chronicle API.
        no_verify: Skip credential verification after saving.

    Raises:
        typer.Exit: If auth modes conflict or required values are missing.

    """
    if sum([bool(api_key), gcp, bool(username or password)]) > 1:
        logger.error("Choose only one auth mode: --gcp, --api-key, or --username/--password.")
        raise typer.Exit(1)

    params = (
        _gather_gcp_params(project, location, instance, credentials_file)
        if gcp
        else _gather_legacy_params(api_root, username, password, api_key)
    )
    config = {k: v for k, v in params._asdict().items() if v is not None}

    with utils.CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(config, f)
    logger.info("Credentials saved to %s", utils.CONFIG_PATH)

    if not no_verify:
        utils.get_backend_api(config)
        logger.info("✅ Credentials verified successfully.")
