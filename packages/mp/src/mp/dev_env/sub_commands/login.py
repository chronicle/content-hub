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

import json
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, NamedTuple

import typer

from mp.dev_env import utils
from mp.telemetry import track_command

if TYPE_CHECKING:
    from mp.core.custom_types import SingleJson

logger: logging.Logger = logging.getLogger(__name__)


login_app: typer.Typer = typer.Typer()


CHRONICLE_API_ROOT_RE: re.Pattern[str] = re.compile(
    r"https?://(?:(?P<location_prefix>[a-z0-9-]+)-)?chronicle\.googleapis\.com/"
    r"(?:v1alpha|v1)/projects/(?P<project>[^/]+)/locations/(?P<location>[^/]+)/"
    r"instances/(?P<instance>[^/]+)",
    re.IGNORECASE,
)


def parse_chronicle_api_root(
    api_root: str | None,
) -> tuple[str | None, str | None, str | None]:
    """Extract project, location, and instance from a Chronicle API root URL.

    Args:
        api_root: The candidate API root URL.

    Returns:
        A tuple of (project, location, instance) or (None, None, None).

    """
    if not api_root:
        return None, None, None
    match: re.Match[str] | None = CHRONICLE_API_ROOT_RE.search(api_root)
    if not match:
        return None, None, None
    project: str | None = match.group("project")
    location: str | None = match.group("location") or match.group("location_prefix")
    instance: str | None = match.group("instance")
    return project, location, instance


class DevEnvParams(NamedTuple):
    """Parameters collected during login to persist to dev-env config file."""

    api_root: str | None
    auth_mode: str
    username: str | None
    password: str | None
    api_key: str | None
    project: str | None
    location: str | None
    instance: str | None
    credentials_file: str | None


@login_app.command(
    name="login",
    help="Login to the development environment (playground).",
)
@track_command
def login(  # ruff:ignore[too-many-arguments, too-many-positional-arguments]
    api_root: Annotated[
        str | None,
        typer.Option(help="API root URL (legacy SOAR or Chronicle API root)."),
    ] = None,
    username: Annotated[
        str | None,
        typer.Option(help="Authentication username (legacy SOAR auth)."),
    ] = None,
    password: Annotated[
        str | None,
        typer.Option(
            help="Authentication password (legacy SOAR auth).",
            hide_input=True,
        ),
    ] = None,
    api_key: Annotated[
        str | None,
        typer.Option(
            help="Authentication API key (legacy SOAR auth).",
            hide_input=True,
        ),
    ] = None,
    project: Annotated[
        str | None,
        typer.Option(help="GCP project ID (--gcp mode)."),
    ] = None,
    location: Annotated[
        str | None,
        typer.Option(help="Chronicle region, e.g. 'us' (--gcp mode)."),
    ] = None,
    instance: Annotated[
        str | None,
        typer.Option(help="Chronicle instance UUID (--gcp mode)."),
    ] = None,
    credentials_file: Annotated[
        str | None,
        typer.Option(
            help="Path to a GCP credentials JSON file (--gcp mode, optional; defaults to ADC).",
        ),
    ] = None,
    *,
    gcp: Annotated[
        bool,
        typer.Option(
            "--gcp/--no-gcp",
            help="Authenticate to the Chronicle API using GCP credentials (ADC).",
        ),
    ] = False,
    no_verify: Annotated[
        bool,
        typer.Option(help="Skip verification after saving."),
    ] = False,
) -> None:
    """Authenticate to the dev environment (playground).

    Supports legacy Siemplify SOAR auth (API key or username/password)
    and Chronicle API using Google Cloud IAM (Service Account JSON or ADC).

    Args:
        api_root: The API root URL of the dev environment.
        username: The username to authenticate with (legacy mode).
        password: The password to authenticate with (legacy mode).
        api_key: The API key for authentication (legacy mode).
        project: GCP project ID (gcp mode).
        location: Chronicle region, e.g. 'us' (gcp mode).
        instance: Chronicle instance UUID (gcp mode).
        credentials_file: Path to a GCP credentials JSON file.
        gcp: Use GCP credentials against the Chronicle API.
        no_verify: Skip credential verification after saving.

    Raises:
        typer.Exit: If auth modes conflict or required values are missing.

    """
    parsed_project: str | None
    parsed_location: str | None
    parsed_instance: str | None
    parsed_project, parsed_location, parsed_instance = parse_chronicle_api_root(api_root)
    is_chronicle_url: bool = (
        parsed_project is not None and parsed_instance is not None
    )
    is_gcp: bool = (
        gcp
        or bool(credentials_file)
        or is_chronicle_url
        or any([project, location, instance])
    )

    if is_gcp and any([username, password, api_key]):
        logger.error(
            "Choose only one auth mode: Chronicle GCP auth or legacy SOAR auth."
        )
        raise typer.Exit(1)
    if not is_gcp and sum([bool(api_key), bool(username or password)]) > 1:
        logger.error(
            "Choose only one auth mode: --api-key or --username/--password."
        )
        raise typer.Exit(1)

    if is_gcp:
        effective_project: str | None = project or parsed_project
        effective_location: str | None = location or parsed_location
        effective_instance: str | None = instance or parsed_instance
        params: DevEnvParams = _gather_gcp_params(
            effective_project,
            effective_location,
            effective_instance,
            credentials_file,
        )
    else:
        params = _gather_legacy_params(api_root, username, password, api_key)

    config: SingleJson = {
        key: value for key, value in params._asdict().items() if value is not None
    }

    with utils.CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(config, f)
    logger.info("Credentials saved to %s", utils.CONFIG_PATH)

    if not no_verify:
        utils.get_backend_api(config)
        logger.info("✅ Credentials verified successfully.")


def _gather_gcp_params(
    project: str | None,
    location: str | None,
    instance: str | None,
    credentials_file: str | None,
) -> DevEnvParams:
    if credentials_file and project is None:
        try:
            creds_path: Path = Path(credentials_file)
            if creds_path.exists():
                creds_data: SingleJson = json.loads(
                    creds_path.read_text(encoding="utf-8")
                )
                project = creds_data.get("project_id")
        except (OSError, json.JSONDecodeError):
            pass

    if project is None:
        project = typer.prompt("GCP project ID")
    if location is None:
        location = typer.prompt("Chronicle region (e.g. us, europe)", default="us")
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
    if api_root is None:
        api_root = typer.prompt("API root (e.g. https://playground.example.com)")
    auth_mode: str
    if api_key is not None:
        auth_mode = "api_key"
        username = None
        password = None
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
