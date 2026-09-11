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

import dataclasses
import json
import logging
import shutil
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import typer

import mp.core.constants
import mp.core.file_utils
from mp.build_project.sub_commands.integration.build import (
    build_integration as build_integration_,
)
from mp.build_project.sub_commands.repository.build import build_repository
from mp.core.custom_types import RepositoryType
from mp.core.data_models.integrations.action.parameter import ActionParamType
from mp.core.data_models.integrations.integration import Integration
from mp.core.data_models.integrations.script.parameter import ScriptParamType
from mp.core.utils import to_snake_case

if TYPE_CHECKING:
    from collections.abc import Callable

    from mp.core.custom_types import SingleJson

logger: logging.Logger = logging.getLogger(__name__)


def get_integration_path(integration: str, src: Path | None = None, *, custom: bool = False) -> Path:
    """Find the source path for a given integration.

    Args:
        integration: The name of the integration to find.
        src: Customize source folder to search from.
        custom: Whether to search in the custom repository.


    Returns:
        The path to the integration's source directory.

    Raises:
        typer.Exit: If the integration directory is not found.

    """
    if src and (src / integration).exists():
        return src / integration

    integrations_root: Path = mp.core.file_utils.create_or_get_integrations_dir()
    if custom:
        source_path = integrations_root / mp.core.constants.CUSTOM_REPO_NAME / integration
        if source_path.exists():
            return source_path

    for repo, folders in mp.core.constants.INTEGRATIONS_DIRS_NAMES_DICT.items():
        if repo == mp.core.constants.THIRD_PARTY_REPO_NAME:
            for folder in folders:
                candidate: Path = integrations_root / repo / folder / integration
                if folder == mp.core.constants.POWERUPS_DIR_NAME:
                    candidate: Path = integrations_root / folder / integration

                if candidate.exists():
                    return candidate
        else:
            candidate: Path = integrations_root / repo / integration
            if candidate.exists():
                return candidate

    logger.error("Could not find source integration at %s/.../%s", integrations_root, integration)
    raise typer.Exit(1)


def get_integration_identifier(source_path: Path) -> str:
    """Get the integration identifier from the non-built integration path.

    Args:
        source_path: Path to the integration source directory.

    Returns:
        str: The integration identifier.

    Raises:
        typer.Exit: If the identifier cannot be determined.

    """
    try:
        integration_obj = Integration.from_non_built_path(source_path)
    except ValueError as e:
        logger.exception("Could not determine integration identifier")
        raise typer.Exit(1) from e
    else:
        return integration_obj.identifier


def build_integration(integration: str, src: Path | None = None, *, custom: bool = False) -> None:
    """Invoke the build command for a single integration.

    Args:
        integration: The name of the integration to build.
        src: Customize source folder to build from.
        custom: build integration from the custom repository.

    Raises:
        typer.Exit: If the build fails.

    """
    try:
        build_integration_([integration], src=src, custom_integration=custom, quiet=True)
        logger.info("Build successful for %s", integration)

    except typer.Exit as e:
        logger.exception("Build failed")
        raise typer.Exit(1) from e


def find_built_integration_dir(identifier: str, src: Path | None = None, *, custom: bool = False) -> Path:
    """Find the built integration directory.

    Args:
        identifier: The integration identifier.
        src: Customize source folder to search from.
        custom: search integration in the out folder of custom repository.


    Returns:
        Path: The path to the built integration directory.

    Raises:
        typer.Exit: If the built integration is not found.

    """
    root: Path = mp.core.file_utils.create_or_get_out_integrations_dir()
    if src and (candidate := root / src.name / identifier).exists():
        return candidate

    if custom:
        candidate = root / mp.core.constants.CUSTOM_REPO_NAME / identifier
        if candidate.exists():
            return candidate

    for repo in mp.core.constants.INTEGRATIONS_DIRS_NAMES_DICT:
        if (candidate := root / repo / identifier).exists():
            return candidate

    logger.error("Built integration not found for identifier '%s' in %s.", identifier, root)
    raise typer.Exit(1)


def zip_integration_dir(integration_dir: Path, *, custom: bool = False) -> Path:
    """Zip the contents of a built integration directory for upload.

    Args:
        integration_dir: Path to the built integration directory.
        custom: Whether the integration is from the custom repository.

    Returns:
        Path: The path to the created zip file.

    """
    if custom:
        _change_integration_to_custom(integration_dir)

    return Path(shutil.make_archive(str(integration_dir), "zip", integration_dir))


def build_integrations_custom_repository() -> None:
    """Build command for all integrations in the custom repository.

    Raises:
        typer.Exit: If the build fails.

    """
    try:
        build_repository([RepositoryType.CUSTOM])

    except typer.Exit as e:
        logger.exception("Build failed")
        raise typer.Exit(1) from e


def zip_integration_custom_repository() -> list[Path]:
    """Zip the contents of the custom repository for upload.

    Returns:
        list[Path]: List of paths to the created zip file.

    """
    custom_repo_out_dir: Path = (
        mp.core.file_utils.create_or_get_out_integrations_dir() / mp.core.constants.CUSTOM_REPO_NAME
    )

    for integration in custom_repo_out_dir.iterdir():
        _change_integration_to_custom(integration)

    return [
        zip_integration_dir(integration_path)
        for integration_path in custom_repo_out_dir.iterdir()
        if integration_path.is_dir()
    ]


def _change_integration_to_custom(built_path: Path) -> None:
    for file in built_path.iterdir():
        if file.name == mp.core.constants.INTEGRATION_DEF_FILE.format(built_path.name):
            _modify_def_file_to_custom(built_path / mp.core.constants.INTEGRATION_DEF_FILE.format(built_path.name))
    if (built_path / mp.core.constants.OUT_ACTIONS_META_DIR).exists():
        _modify_def_files_to_custom(
            built_path / mp.core.constants.OUT_ACTIONS_META_DIR,
            mp.core.constants.ACTIONS_META_SUFFIX,
        )
    if (built_path / mp.core.constants.OUT_CONNECTORS_META_DIR).exists():
        _modify_def_files_to_custom(
            built_path / mp.core.constants.OUT_CONNECTORS_META_DIR,
            mp.core.constants.CONNECTORS_META_SUFFIX,
        )
    if (built_path / mp.core.constants.OUT_JOBS_META_DIR).exists():
        _modify_def_files_to_custom(
            built_path / mp.core.constants.OUT_JOBS_META_DIR, mp.core.constants.JOBS_META_SUFFIX
        )


def _modify_def_files_to_custom(def_files_dir: Path, suffix: str) -> None:
    for file in def_files_dir.iterdir():
        if file.suffix == suffix:
            _modify_def_file_to_custom(file)


def _modify_def_file_to_custom(file: Path) -> None:
    try:
        with Path.open(file, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["IsCustom"] = True

        with Path.open(file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, sort_keys=True)

    except (OSError, json.JSONDecodeError):
        logger.exception("Failed to process %s", file)


def save_integration_as_zip(integration_name: str, data: bytes, dst: Path) -> Path:
    """Save raw integration ZIP bytes into a file.

    Args:
        integration_name: The name of the integration to save.
        data: The raw integration package ZIP bytes.
        dst: The directory where the ZIP file should be saved.

    Returns:
        Path: The path to the saved ZIP file.

    """
    zip_path = dst / f"{integration_name}.zip"
    zip_path.write_bytes(data)
    return zip_path


def unzip_integration(zip_path: Path, temp_path: Path) -> Path:
    """Unzips an integration to a destination and normalizes built structure for deconstruction.

    Args:
        zip_path: The path to the source ZIP file.
        temp_path: temp path that the built integration will be extracted to.

    Returns:
        A path to the successfully extracted folder.

    """
    dest: Path = temp_path / zip_path.stem
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(dest)

    _normalize_unzipped_integration(dest)
    return dest


@dataclasses.dataclass(frozen=True)
class _SubfolderConfig:
    sub: str
    def_dir: str
    script_dir: str
    suffix: str
    normalizer: Callable[[SingleJson, str], None]


def _normalize_unzipped_integration(dest: Path) -> None:
    identifier: str = ""
    json_defs: list[Path] = list(dest.glob("Integration-*.json"))
    for json_def in json_defs:
        identifier = _normalize_integration_def(json_def)

    subfolder_configs: list[_SubfolderConfig] = [
        _SubfolderConfig(
            "Actions",
            mp.core.constants.OUT_ACTIONS_META_DIR,
            mp.core.constants.OUT_ACTION_SCRIPTS_DIR,
            mp.core.constants.ACTIONS_META_SUFFIX,
            _normalize_action_def,
        ),
        _SubfolderConfig(
            "Connectors",
            mp.core.constants.OUT_CONNECTORS_META_DIR,
            mp.core.constants.OUT_CONNECTOR_SCRIPTS_DIR,
            mp.core.constants.CONNECTORS_META_SUFFIX,
            _normalize_connector_def,
        ),
        _SubfolderConfig(
            "Jobs",
            mp.core.constants.OUT_JOBS_META_DIR,
            mp.core.constants.OUT_JOB_SCRIPTS_DIR,
            mp.core.constants.JOBS_META_SUFFIX,
            _normalize_job_def,
        ),
        _SubfolderConfig(
            "Widgets",
            mp.core.constants.OUT_WIDGETS_META_DIR,
            mp.core.constants.OUT_WIDGET_SCRIPTS_DIR,
            mp.core.constants.JSON_SUFFIX,
            _normalize_widget_def,
        ),
    ]
    for cfg in subfolder_configs:
        _normalize_subfolder(dest, cfg, identifier)


def _normalize_script_param_type(
    raw_type: Any,
    default: int = ScriptParamType.STRING.value,
) -> int:
    """Normalize a raw script or connector parameter type to its integer enum value."""
    if isinstance(raw_type, str):
        try:
            return ScriptParamType.from_string(raw_type).value
        except KeyError:
            try:
                return int(raw_type)
            except ValueError:
                return default
    try:
        return int(raw_type)
    except (ValueError, TypeError):
        return default


def _normalize_action_param_type(
    raw_type: Any,
    default: int = ActionParamType.STRING.value,
) -> int:
    """Normalize a raw action parameter type to its integer enum value."""
    if isinstance(raw_type, str):
        try:
            return ActionParamType.from_string(raw_type).value
        except KeyError:
            try:
                return int(raw_type)
            except ValueError:
                return default
    try:
        return int(raw_type)
    except (ValueError, TypeError):
        return default


def _normalize_integration_properties(def_data: SingleJson, identifier: str) -> None:
    props: Any = (
        def_data.get("IntegrationProperties") or def_data.get("Parameters") or []
    )
    for prop in props:
        if isinstance(prop, dict):
            prop.setdefault("PropertyName", prop.get("PropertyName", ""))
            prop.setdefault(
                "PropertyDisplayName",
                prop.get("DisplayName") or prop.get("PropertyDisplayName") or prop.get("PropertyName", ""),
            )
            prop.setdefault("Value", prop.get("DefaultValue"))
            prop.setdefault("PropertyDescription", prop.get("Description", ""))
            prop.setdefault("IsMandatory", prop.get("Mandatory", False))
            prop.setdefault("IntegrationIdentifier", identifier)
            prop["PropertyType"] = _normalize_script_param_type(
                prop.get("PropertyType", prop.get("Type", 2)),
                default=ScriptParamType.STRING.value,
            )

    def_data["IntegrationProperties"] = props


def _normalize_integration_def(json_def: Path) -> str:
    try:
        raw_text: str = json_def.read_text(encoding="utf-8")
        def_data: SingleJson = json.loads(raw_text)
    except (OSError, json.JSONDecodeError):
        logger.exception("Failed to read %s", json_def)
        return ""

    identifier: str = def_data.get("Identifier") or json_def.stem.replace("Integration-", "")
    svg_img: Any = def_data.get("SvgIcon") or def_data.get("SVGImage") or ""
    def_data.setdefault("SvgImage", svg_img)
    def_data.setdefault("SVGImage", svg_img)
    def_data["DocumentationLink"] = def_data.get("DocumentationLink") or None
    display_name: str = def_data.get("DisplayName") or def_data.get("Name") or identifier
    def_data.setdefault("DisplayName", display_name)
    def_data.setdefault("MarketingDisplayName", display_name)
    def_data.setdefault("MinimumSystemVersion", 1.0)
    def_data.setdefault("ImageBase64", def_data.get("ImageBase64") or "")
    def_data.setdefault("IsCustom", True)
    def_data.setdefault("IsPowerUp", False)
    def_data.setdefault("IsCertified", def_data.get("Certified", False))
    def_data.setdefault("ShouldInstalledInSystem", False)
    def_data.setdefault("IsAvailableForCommunity", True)

    version: Any = def_data.get("Version")
    if version is None:
        def_data["Version"] = 1.0
    else:
        try:
            def_data["Version"] = float(version)
        except (ValueError, TypeError):
            def_data["Version"] = 1.0

    py_ver: Any = def_data.get("PythonVersion")
    if py_ver in {"V3_11", "3.11", "3", 3, None}:
        def_data["PythonVersion"] = 3
    elif py_ver in {"V2_7", "2.7", "2", 2}:
        def_data["PythonVersion"] = 2

    _normalize_integration_properties(def_data, identifier)

    try:
        def_file: Path = json_def.with_suffix(".def")
        def_file.write_text(json.dumps(def_data, indent=4), encoding="utf-8")
        json_def.unlink()
    except OSError:
        logger.exception("Failed to write normalized def file for %s", json_def)

    return identifier


def _normalize_action_def(item_def: SingleJson, identifier: str) -> None:
    item_def.setdefault("Creator", item_def.get("Author") or "admin")
    item_def.setdefault("IntegrationIdentifier", item_def.get("Integration") or identifier)
    item_def.setdefault("IsAsync", item_def.get("Async", False))
    item_def.setdefault("IsEnabled", item_def.get("Enabled", True))
    item_def.setdefault("IsCustom", item_def.get("Custom", True))
    item_def.setdefault("DynamicResultsMetadata", item_def.get("DynamicResults") or [])
    item_def.setdefault("SimulationDataJson", '{"Entities": []}')
    try:
        item_def["Version"] = float(item_def.get("Version") or 1.0)
    except (ValueError, TypeError):
        item_def["Version"] = 1.0
    item_def.setdefault("AiCategories", item_def.get("AICategories") or [])
    item_def.setdefault("AiDescription", item_def.get("AIDescription"))
    item_def.setdefault("AiShortDescription", item_def.get("AiShortDescription"))
    item_def.setdefault("ParametersDescription", item_def.get("ParametersDescription"))
    item_def.setdefault("EntityTypes", item_def.get("EntityTypes") or [])
    item_def.setdefault("OutcomeCategories", item_def.get("OutcomeCategories") or [])
    for ap in item_def.get("Parameters", []):
        if isinstance(ap, dict):
            ap.setdefault("Name", ap.get("DisplayName") or ap.get("Name", ""))
            ap.setdefault("Description", ap.get("Description", ""))
            ap.setdefault("IsMandatory", ap.get("Mandatory", False))
            ap.setdefault("OptionalValues", ap.get("OptionalValues") or [])
            ap["Type"] = _normalize_action_param_type(
                ap.get("Type", 0),
                default=ActionParamType.STRING.value,
            )
            ap.setdefault("DefaultValue", ap.get("DefaultValue"))


def _normalize_connector_def(item_def: SingleJson, identifier: str) -> None:
    item_def.setdefault("Creator", item_def.get("Author") or "admin")
    item_def.setdefault("Integration", item_def.get("Integration") or identifier)
    item_def.setdefault("IsCustom", item_def.get("Custom", True))
    item_def.setdefault("IsEnabled", item_def.get("Enabled", True))
    item_def.setdefault(
        "IsConnectorRulesSupported",
        item_def.get("ConnectorRulesSupported", False),
    )
    item_def.setdefault("Name", item_def.get("DisplayName") or item_def.get("Name", ""))
    item_def.setdefault("Rules", item_def.get("Rules") or [])
    try:
        item_def["Version"] = float(item_def.get("Version") or 1.0)
    except (ValueError, TypeError):
        item_def["Version"] = 1.0
    for cp in item_def.get("Parameters", []):
        if isinstance(cp, dict):
            cp.setdefault("Name", cp.get("DisplayName") or cp.get("Name", ""))
            cp["Description"] = cp.get("Description") or ""
            cp.setdefault("IsMandatory", cp.get("Mandatory", False))
            cp.setdefault("IsAdvanced", cp.get("IsAdvanced", False))
            cp.setdefault("DefaultValue", cp.get("DefaultValue"))
            cp.setdefault("Mode", cp.get("Mode", 0))
            cp["Type"] = _normalize_script_param_type(
                cp.get("Type", 2),
                default=ScriptParamType.STRING.value,
            )


def _normalize_job_def(item_def: SingleJson, identifier: str) -> None:
    item_def.setdefault("Creator", item_def.get("Author") or "admin")
    item_def.setdefault("Integration", item_def.get("Integration") or identifier)
    item_def.setdefault("IsCustom", item_def.get("Custom", True))
    item_def.setdefault("IsEnabled", item_def.get("Enabled", True))
    item_def.setdefault("Name", item_def.get("DisplayName") or item_def.get("Name", ""))
    item_def.setdefault("RunIntervalInSeconds", item_def.get("RunIntervalInSeconds", 3600))
    try:
        item_def["Version"] = float(item_def.get("Version") or 1.0)
    except (ValueError, TypeError):
        item_def["Version"] = 1.0
    for jp in item_def.get("Parameters", []):
        if isinstance(jp, dict):
            jp.setdefault("Name", jp.get("DisplayName") or jp.get("Name", ""))
            jp.setdefault("Description", jp.get("Description", ""))
            jp.setdefault("IsMandatory", jp.get("Mandatory", False))
            jp.setdefault("DefaultValue", jp.get("DefaultValue"))
            jp["Type"] = _normalize_script_param_type(
                jp.get("Type", 2),
                default=ScriptParamType.STRING.value,
            )


def _normalize_widget_def(item_def: SingleJson, _identifier: str) -> None:
    item_def.setdefault("Title", item_def.get("Title") or item_def.get("Name", ""))
    item_def.setdefault("Type", item_def.get("Type", 0))
    item_def.setdefault("Scope", item_def.get("Scope", 0))
    item_def.setdefault("ActionIdentifier", item_def.get("ActionIdentifier", ""))
    item_def.setdefault("Description", item_def.get("Description", ""))
    item_def.setdefault("DataDefinition", item_def.get("DataDefinition", {}))
    item_def.setdefault("ConditionsGroup", item_def.get("ConditionsGroup", {}))
    item_def.setdefault("DefaultSize", item_def.get("DefaultSize", 0))


def _normalize_subfolder(
    dest: Path,
    cfg: _SubfolderConfig,
    identifier: str,
) -> None:
    src_sub: Path = dest / cfg.sub
    if not (src_sub.exists() and src_sub.is_dir()):
        return

    staging_dir: Path = dest / f"__temp_{cfg.sub}"
    src_sub.rename(staging_dir)

    target_defs: Path = dest / cfg.def_dir
    target_scripts: Path = dest / cfg.script_dir
    target_defs.mkdir(parents=True, exist_ok=True)
    target_scripts.mkdir(parents=True, exist_ok=True)

    files_list: list[Path] = list(staging_dir.iterdir())
    for sub_file in files_list:
        if sub_file.suffix == ".json":
            try:
                item_def: SingleJson = json.loads(
                    sub_file.read_text(encoding="utf-8")
                )
                cfg.normalizer(item_def, identifier)
                out_path: Path = target_defs / f"{sub_file.stem}{cfg.suffix}"
                out_path.write_text(
                    json.dumps(item_def, indent=4),
                    encoding="utf-8",
                )
            except (OSError, json.JSONDecodeError):
                logger.exception("Failed to normalize %s", sub_file)
        elif sub_file.suffix in {".py", ".html"}:
            shutil.move(sub_file, target_scripts / sub_file.name)

    shutil.rmtree(staging_dir, ignore_errors=True)


def deconstruct_integration(built_integration: Path, dst: Path) -> Path:
    """Deconstructs a built integration and restores the source to its original directory.

    Args:
        built_integration (Path): Path to the built integration folder.
        dst (Path): Destination folder.

    Returns:
        Path: Path to the deconstructed integration.

    Raises:
        typer.Exit: If the deconstruction subprocess fails.

    """
    try:
        build_integration_(
            [built_integration.stem],
            src=built_integration.parent,
            dst=dst,
            deconstruct=True,
            quiet=True,
        )
        return dst / to_snake_case(built_integration.stem)

    except typer.Exit as e:
        logger.exception("Deconstruct failed")
        raise typer.Exit(1) from e
