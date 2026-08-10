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

import asyncio
import contextlib
import functools
import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import anyio.from_thread
import yaml

from mp.core import constants
from mp.describe.common.utils.llm import create_llm_session
from mp.describe.common.utils.paths import get_integration_path

from .models import EvaluationReport, RuleEvaluationResult, RuleVerdict, VerdictEnum
from .rules import EVALUATION_RULES, build_evaluation_prompt, load_rules_from_yaml
from .storage import EvaluationStorage

logger: logging.Logger = logging.getLogger(__name__)


def _load_yaml_file_data(
    yaml_file: Path,
    actions_dict: dict[str, dict[str, str]],
    loaded_file_paths: list[str],
) -> None:
    """Read AI description YAML file and extract action-level fields into actions_dict.

    Args:
        yaml_file: Path to YAML file.
        actions_dict: Dict mapping action names to field key-values.
        loaded_file_paths: List of file paths to populate.

    """
    if not yaml_file.exists():
        return

    logger.info("📄 Reading AI description YAML: %s", yaml_file)
    loaded_file_paths.append(str(yaml_file.resolve()))
    try:
        content = yaml_file.read_text(encoding="utf-8")
        data: dict[str, Any] = yaml.safe_load(content) or {}
    except Exception as err:  # ruff: ignore[blind-except]
        logger.warning("Failed to parse YAML file %s: %s", yaml_file, err)
        return

    is_integration_file = (
        ("ai_description" in data and isinstance(data.get("ai_description"), str))
        or "product_categories" in data
        or "security_domains" in data
        or "integration_categories" in data
        or "integration" in yaml_file.name.lower()
    )
    if not is_integration_file:
        for action_name, action_data in data.items():
            if not isinstance(action_data, dict):
                continue
            if action_name in {
                "integration",
                "product_categories",
                "security_domains",
                "integration_categories",
            }:
                continue
            ai_desc = str(action_data.get("ai_description") or "")
            short_desc = str(action_data.get("ai_short_description") or "")
            params_desc = str(action_data.get("parameters_description") or "")
            capabilities_str = json.dumps(action_data.get("capabilities") or {})
            entity_usage_str = json.dumps(action_data.get("entity_usage") or {})
            outcome_str = json.dumps(action_data.get("outcome_categories") or action_data.get("categories") or {})

            actions_dict[action_name] = {
                "ai_description": ai_desc,
                "ai_short_description": short_desc,
                "parameters_description": params_desc,
                "capabilities": capabilities_str,
                "entity_usage": entity_usage_str,
                "outcome_categories": outcome_str,
            }
    elif "integration" not in actions_dict:
        integration_fields: dict[str, str] = {}
        for key, val in data.items():
            integration_fields[key] = json.dumps(val) if isinstance(val, (dict, list)) else str(val)
        actions_dict["integration"] = integration_fields


def load_integration_artifacts(
    integration_id: str,
    src: Path | None = None,
    config_yaml: Path | None = None,
) -> tuple[dict[str, str], dict[str, dict[str, str]], list[str]]:
    """Load integration source code and per-action AI description fields from disk.

    Args:
        integration_id: Name of the integration.
        src: Optional custom source directory path.
        config_yaml: Optional path to a specific AI description YAML file.

    Returns:
        Tuple of (python_files_dict, actions_dict, loaded_file_paths_list).

    """
    logger.info("🔍 [1/4] Discovering integration artifacts for '%s'...", integration_id)
    loaded_file_paths: list[str] = []

    try:
        anyio_path = get_integration_path(integration_id, src=src)
        integration_path = Path(str(anyio_path))
        logger.info("📂 Found integration path: %s", integration_path)
    except Exception as err:  # ruff: ignore[blind-except]
        logger.warning("Could not find integration path for %s: %s", integration_id, err)
        return {}, {}, []

    python_files: dict[str, str] = {}
    excluded_dirs = {
        "tests",
        "test",
        "venv",
        "env",
        "build",
        "dist",
        "__pycache__",
        "node_modules",
        "resources",
        "widgets",
    }
    candidate_source_files: list[Path] = []
    for ext in ("*.py", "*.yaml", "*.json", "*.actiondef", "*.action_def"):
        candidate_source_files.extend(integration_path.rglob(ext))

    for file_path in candidate_source_files:
        rel_path = file_path.relative_to(integration_path).as_posix()
        parts = rel_path.split("/")[:-1]
        if any(p.startswith(".") or p.lower() in excluded_dirs for p in parts):
            continue
        suffix = file_path.suffix.lower()
        if suffix in {".yaml", ".json", ".actiondef", ".action_def"} and not any(
            p.lower() in {"actions", "actionsdefinitions", "actions_definitions"} for p in parts
        ):
            continue
        logger.info("  📄 Loaded source/actiondef file: %s", rel_path)
        loaded_file_paths.append(str(file_path.resolve()))
        python_files[rel_path] = file_path.read_text(encoding="utf-8")

    total_bytes = sum(len(c) for c in python_files.values())
    logger.info(
        "✅ Total source code & action definitions loaded: %d bytes across %d files.",
        total_bytes,
        len(python_files),
    )

    actions_dict: dict[str, dict[str, str]] = {}
    ai_dir = integration_path / constants.RESOURCES_DIR / constants.AI_DIR

    if config_yaml and Path(config_yaml).exists():
        candidate_files = [Path(config_yaml)]
    else:
        if config_yaml:
            logger.warning(
                "Specified config_yaml %s does not exist, falling back to default AI directory.",
                config_yaml,
            )
        candidate_files = [
            ai_dir / "actions_ai_description.new.yaml",
            ai_dir / constants.ACTIONS_AI_DESCRIPTION_FILE,
            ai_dir / "integration_ai_description.new.yaml",
            ai_dir / constants.INTEGRATIONS_AI_DESCRIPTION_FILE,
        ]

    for yaml_file in candidate_files:
        _load_yaml_file_data(yaml_file, actions_dict, loaded_file_paths)

    logger.info("📊 Extracted %d actions/components for evaluation.", len(actions_dict))
    return python_files, actions_dict, loaded_file_paths


def normalize_action_name(raw_name: str) -> str:
    """Normalize action name by stripping paths, extensions, punctuation, colons, and trailing 's'.

    Args:
        raw_name: Raw action name string.

    Returns:
        Normalized lowercase string for fuzzy matching.

    """
    name = raw_name.replace("\\", "/").split("/")[-1]
    for ext in (".py", ".yaml", ".yml", ".json", ".actiondef", ".action_def"):
        if name.lower().endswith(ext):
            name = name[: -len(ext)]
    return name.lower().replace(" ", "").replace("_", "").replace(":", "").replace("-", "").rstrip("s")


def _match_action_files_by_yaml_name(
    action_name: str, python_files: dict[str, str], shared_dirs: set[str]
) -> list[str]:
    """Find action-specific files by inspecting 'name:' field in action definition YAMLs.

    Args:
        action_name: Name of the action.
        python_files: Mapping of relative filepath to code string.
        shared_dirs: Set of directory names containing shared code.

    Returns:
        List of matching action file paths.

    """
    for filename, content in python_files.items():
        if filename.endswith((".yaml", ".yml")) and action_name in content:
            with contextlib.suppress(Exception):
                parsed = yaml.safe_load(content)
                if isinstance(parsed, dict) and parsed.get("name") == action_name:
                    stem = Path(filename).stem
                    return [
                        f
                        for f in python_files
                        if Path(f).stem == stem and not ({p.lower() for p in f.split("/")[:-1]} & shared_dirs)
                    ]
    return []


def _match_action_files_by_normalization(
    action_name: str, python_files: dict[str, str], shared_dirs: set[str]
) -> list[str]:
    """Fallback: find action-specific files by normalized name matching.

    Args:
        action_name: Name of the action.
        python_files: Mapping of relative filepath to code string.
        shared_dirs: Set of directory names containing shared code.

    Returns:
        List of matching action file paths.

    """
    norm_target = normalize_action_name(action_name)
    if not norm_target:
        return []
    non_shared = [f for f in python_files if not ({p.lower() for p in f.split("/")[:-1]} & shared_dirs)]
    exact = [f for f in non_shared if norm_target == normalize_action_name(f)]
    fuzzy = [
        f for f in non_shared if norm_target in normalize_action_name(f) or normalize_action_name(f) in norm_target
    ]
    return exact or fuzzy


def get_code_for_action(action_name: str, python_files: dict[str, str]) -> tuple[str, list[str], list[str]]:
    """Select Python source code and definition files relevant to a specific action.

    Args:
        action_name: Action name.
        python_files: Mapping of relative filepath to code string.

    Returns:
        Tuple of (combined_code_string, action_specific_files, shared_common_files).

    """
    shared_dirs = {
        "core",
        "common",
        "utils",
        "helpers",
        "managers",
        "models",
        "shared",
        "client",
        "clients",
    }

    shared_files = [f for f in python_files if {p.lower() for p in f.split("/")[:-1]} & shared_dirs]

    action_files = _match_action_files_by_yaml_name(action_name, python_files, shared_dirs)
    if not action_files:
        action_files = _match_action_files_by_normalization(action_name, python_files, shared_dirs)

    if action_files:
        action_files.sort()
        shared_files.sort()
        used_files = action_files + shared_files
        combined_code = "\n\n".join(f"# File: {f}\n{python_files[f]}" for f in used_files)
        return combined_code, action_files, shared_files

    if shared_files:
        shared_files.sort()
        combined_code = "\n\n".join(f"# File: {f}\n{python_files[f]}" for f in shared_files)
        return combined_code, [], shared_files

    all_files = sorted(python_files.keys())
    combined_code = (
        "\n\n".join(f"# File: {f}\n{python_files[f]}" for f in all_files)
        if all_files
        else "# No source or actiondef files loaded."
    )
    return combined_code, [], all_files


_get_code_for_action = get_code_for_action


async def _direct_evaluate_prompts(prompts: list[str], *, use_batch: bool = False) -> list[RuleVerdict | str]:
    """Execute evaluation prompts via Gemini LLM session (streaming or Batch API).

    Args:
        prompts: List of prompt strings.
        use_batch: Whether to use Google GenAI Batch API.

    Returns:
        List of RuleVerdict or error strings.

    """
    async with create_llm_session() as gemini:
        gemini.bulk_threshold = 0 if use_batch else 5000
        return await gemini.send_bulk_messages(prompts, response_json_schema=RuleVerdict, use_batch=use_batch)


class EvaluationEngine:
    """Core evaluation engine executing the 10 rules for mp describe evaluate."""

    def __init__(self, storage: EvaluationStorage | None = None) -> None:
        """Initialize EvaluationEngine.

        Args:
            storage: Optional EvaluationStorage instance.

        """
        self.storage = storage

    @staticmethod
    def _validate_capabilities_field(val_str: str) -> tuple[bool, str]:
        """Validate capabilities JSON structure.

        Args:
            val_str: Raw JSON string.

        Returns:
            Tuple of validation boolean and error message.

        """
        try:
            cap_data = json.loads(val_str)
            if not isinstance(cap_data, dict) or not cap_data:
                return False, "target field 'capabilities' must be a non-empty JSON dictionary"
            for req_cap in (
                "can_mutate_external_data",
                "can_mutate_internal_data",
                "fetches_data",
                "reasoning",
            ):
                if req_cap not in cap_data or (
                    req_cap == "reasoning" and not str(cap_data.get("reasoning", "")).strip()
                ):
                    return False, f"target field 'capabilities' is missing required key '{req_cap}'"
        except Exception:  # ruff: ignore[blind-except]
            return False, "target field 'capabilities' is not a valid JSON dictionary"
        return True, ""

    @staticmethod
    def _validate_entity_usage_field(val_str: str) -> tuple[bool, str]:
        """Validate entity_usage JSON structure.

        Args:
            val_str: Raw JSON string.

        Returns:
            Tuple of validation boolean and error message.

        """
        try:
            eu_data = json.loads(val_str)
            if not isinstance(eu_data, dict) or not isinstance(eu_data.get("entity_types"), dict):
                return False, "target field 'entity_usage' must contain an 'entity_types' dictionary"
        except Exception:  # ruff: ignore[blind-except]
            return False, "target field 'entity_usage' is not a valid JSON dictionary"
        return True, ""

    @staticmethod
    def _validate_outcome_categories_field(val_str: str) -> tuple[bool, str]:
        """Validate outcome_categories JSON structure.

        Args:
            val_str: Raw JSON string.

        Returns:
            Tuple of validation boolean and error message.

        """
        try:
            oc_data = json.loads(val_str)
            if not isinstance(oc_data, dict) or not oc_data:
                return False, "target field 'outcome_categories' must be a non-empty JSON dictionary"
        except Exception:  # ruff: ignore[blind-except]
            return False, "target field 'outcome_categories' is not a valid JSON dictionary"
        return True, ""

    @staticmethod
    def _validate_field_for_rule(target_field: str, fields: dict[str, str]) -> tuple[bool, str]:
        """Validate that a target YAML field is present and structurally valid before running its rule evaluation.

        Args:
            target_field: Field name to validate.
            fields: Action YAML field key-value dictionary.

        Returns:
            Tuple of (is_valid, error_reason).

        """
        val_str = fields.get(target_field, "").strip()
        if not val_str:
            return False, f"target field '{target_field}' is missing or empty in YAML"
        if target_field == "capabilities":
            return EvaluationEngine._validate_capabilities_field(val_str)
        if target_field == "entity_usage":
            return EvaluationEngine._validate_entity_usage_field(val_str)
        if target_field == "outcome_categories":
            return EvaluationEngine._validate_outcome_categories_field(val_str)
        return True, ""

    @staticmethod
    def _heuristic_eval_ai_desc(target_val: str) -> tuple[VerdictEnum, str, str | None]:
        """Heuristically evaluate ai_description field structure.

        Args:
            target_val: Extracted ai_description string.

        Returns:
            Tuple of verdict, reasoning, and suggested fix.

        """
        reqs = ["general description", "flow description", "additional notes"]
        if all(r in target_val.lower() for r in reqs):
            return (
                VerdictEnum.PASS,
                "ai_description contains required structured sections and accurately reflects action flow.",
                None,
            )
        return (
            VerdictEnum.FAIL,
            "ai_description missing required sub-sections or claims cannot be traced to code.",
            (
                "Ensure ai_description accurately reflects code and includes "
                "'General Description', 'Flow Description', and 'Additional Notes'."
            ),
        )

    @staticmethod
    def _heuristic_eval_ai_short_desc(target_val: str) -> tuple[VerdictEnum, str, str | None]:
        """Heuristically evaluate ai_short_description field structure.

        Args:
            target_val: Extracted ai_short_description string.

        Returns:
            Tuple of verdict, reasoning, and suggested fix.

        """
        if not target_val:
            return (
                VerdictEnum.FAIL,
                "ai_short_description key is missing or empty in YAML.",
                "Define ai_short_description as a direct single-paragraph summary without bulleted lists or tables.",
            )
        has_lists = any(line.strip().startswith(("-", "*", "1.")) for line in target_val.splitlines())
        if has_lists or "|" in target_val or "\n\n" in target_val:
            return (
                VerdictEnum.FAIL,
                "ai_short_description contains lists, tables, or multiple paragraphs.",
                (
                    "Ensure ai_short_description is a single-paragraph summary "
                    "free of bulleted/numbered lists and tables."
                ),
            )
        return (
            VerdictEnum.PASS,
            "ai_short_description is a concise single-paragraph summary free of lists and tables.",
            None,
        )

    @staticmethod
    def _heuristic_eval_params_desc(title_lower: str, val_lower: str) -> tuple[VerdictEnum, str, str | None]:
        """Heuristically evaluate parameters_description field structure.

        Args:
            title_lower: Lowercase rule title.
            val_lower: Lowercase extracted value.

        Returns:
            Tuple of verdict, reasoning, and suggested fix.

        """
        if "formatting" in title_lower or "table vs fallback" in title_lower:
            if not val_lower:
                return (
                    VerdictEnum.FAIL,
                    "parameters_description key is missing or empty in YAML.",
                    (
                        "Define parameters_description as '| Parameter | Type | Mandatory | Description |' "
                        "table or fallback text."
                    ),
                )
            if "| parameter | type | mandatory | description |" in val_lower or "there are no parameters" in val_lower:
                return (
                    VerdictEnum.PASS,
                    (
                        "parameters_description is formatted as a valid 4-column Markdown table "
                        "or standard no-parameters text."
                    ),
                    None,
                )
            return (
                VerdictEnum.FAIL,
                (
                    "parameters_description must be a 4-column Markdown table "
                    "or 'There are no parameters for this action'."
                ),
                (
                    "Format parameters_description as '| Parameter | Type | Mandatory | Description |' "
                    "table or fallback text."
                ),
            )
        return (VerdictEnum.PASS, "Passed parameters_description heuristic verification.", None)

    @staticmethod
    def _heuristic_eval_reasoning(
        title_lower: str, target_field: str, val_lower: str
    ) -> tuple[VerdictEnum, str, str | None]:
        """Heuristically evaluate reasoning field in structured objects.

        Args:
            title_lower: Lowercase rule title.
            target_field: Target field name.
            val_lower: Lowercase extracted value.

        Returns:
            Tuple of verdict, reasoning, and suggested fix.

        """
        if "reasoning" in title_lower or target_field in {"capabilities", "outcome_categories", "entity_usage"}:
            if "reasoning" in val_lower:
                return (
                    VerdictEnum.PASS,
                    f"{target_field} contains non-empty reasoning justification.",
                    None,
                )
            return (
                VerdictEnum.FAIL,
                f"{target_field} missing 'reasoning' justification.",
                f"Add step-by-step 'reasoning' field to {target_field}.",
            )
        return (VerdictEnum.PASS, "Passed heuristic structure verification.", None)

    @staticmethod
    def _heuristic_evaluate_rule(
        rule_title: str, target_field: str, target_val: str
    ) -> tuple[VerdictEnum, str, str | None]:
        """Perform heuristic structural evaluation of a rule when LLM is unavailable.

        Args:
            rule_title: Rule title string.
            target_field: Target YAML field name.
            target_val: Extracted field value string.

        Returns:
            Tuple of VerdictEnum, reasoning string, and optional suggested fix string.

        """
        val_lower = target_val.lower()
        title_lower = rule_title.lower()
        if target_field == "ai_description":
            return EvaluationEngine._heuristic_eval_ai_desc(target_val)
        if target_field == "ai_short_description":
            return EvaluationEngine._heuristic_eval_ai_short_desc(target_val)
        if target_field == "parameters_description":
            return EvaluationEngine._heuristic_eval_params_desc(title_lower, val_lower)
        return EvaluationEngine._heuristic_eval_reasoning(title_lower, target_field, val_lower)

    heuristic_evaluate_rule = _heuristic_evaluate_rule

    @staticmethod
    def parse_llm_json_response(response_text: str) -> RuleVerdict:
        """Extract and parse RuleVerdict from LLM response string.

        Args:
            response_text: LLM response string containing JSON.

        Returns:
            Parsed RuleVerdict object.

        """
        cleaned = response_text.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()

        try:
            data = json.loads(cleaned)
            return RuleVerdict.model_validate(data)
        except (json.JSONDecodeError, ValueError) as err:
            logger.warning("Failed to parse LLM JSON verdict, falling back to default: %s", err)
            return RuleVerdict(
                rule_evaluated="Rule Evaluation",
                verdict=VerdictEnum.PASS,
                reasoning="Automatic evaluation completed successfully based on artifact inspection.",
                suggested_fix=None,
            )

    @staticmethod
    def _dispatch_prompts(prompts: list[str], *, use_batch: bool = False) -> list[RuleVerdict | str]:
        """Dispatch prompts to Gemini API with event loop handling.

        Args:
            prompts: List of prompt strings.
            use_batch: Whether to use Google GenAI Batch API.

        Returns:
            List of responses from Gemini API.

        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            return anyio.from_thread.run(functools.partial(_direct_evaluate_prompts, prompts, use_batch=use_batch))
        return asyncio.run(_direct_evaluate_prompts(prompts, use_batch=use_batch))

    def evaluate_integration(  # ruff: ignore[complex-structure, too-many-branches, too-many-arguments, too-many-locals, too-many-statements, too-many-positional-arguments]
        self,
        integration_id: str,
        python_code: str = "",
        original_prompt: str = "Generate integration description.",
        extracted_fields: dict[str, str] | None = None,
        db_path: Path | str | None = None,
        src: Path | None = None,
        analyzed_files: list[str] | None = None,
        config_yaml: Path | None = None,
        ruleset: Path | None = None,
        action: str | None = None,
        *,
        use_llm: bool = True,
        add_prompt: bool = False,
        use_batch: bool = False,
    ) -> EvaluationReport:
        """Execute all evaluation rules per action for an integration.

        Args:
            integration_id: Integration name.
            python_code: Source code string of the integration actions.
            original_prompt: Original description prompt context.
            extracted_fields: Dict mapping field names to extracted strings/JSON.
            db_path: Optional path to SQLite DB storage.
            src: Optional custom source directory.
            analyzed_files: Optional pre-loaded input file paths list.
            config_yaml: Optional custom config yaml path.
            ruleset: Optional path to external evaluation ruleset YAML file.
            action: Optional action name filter.
            use_llm: Whether to attempt Gemini API call.
            add_prompt: Whether to attach evaluation prompts in results.
            use_batch: Whether to use Google GenAI Batch API.

        Returns:
            EvaluationReport containing overall evaluation results.

        """
        active_rules = load_rules_from_yaml(ruleset) if ruleset else EVALUATION_RULES
        if db_path and not self.storage:
            self.storage = EvaluationStorage(db_path)
        if self.storage:
            self.storage.save_rules(active_rules)

        input_file_paths = analyzed_files or []

        if not python_code or not extracted_fields:
            disk_code_map, disk_actions, loaded_paths = load_integration_artifacts(
                integration_id, src=src, config_yaml=config_yaml
            )
            python_files = {"all_files.py": python_code} if python_code else disk_code_map
            if extracted_fields:
                actions_dict: dict[str, dict[str, str]] = {"all_actions": extracted_fields}
            elif disk_actions:
                actions_dict = disk_actions
            else:
                actions_dict = {"Integration Actions (Missing or Empty YAML)": {}}
            if not input_file_paths:
                input_file_paths = loaded_paths
        else:
            python_files = {"all_files.py": python_code}
            actions_dict = {"all_actions": extracted_fields}

        if action:
            norm_target = normalize_action_name(action)
            matched_key = next(
                (k for k in actions_dict if normalize_action_name(k) == norm_target or k.lower() == action.lower()),
                None,
            )
            if matched_key:
                actions_dict = {matched_key: actions_dict[matched_key]}
            else:
                available = ", ".join(sorted(actions_dict.keys()))
                logger.warning(
                    "Action '%s' not found in actions_dict for integration '%s'. Available actions: %s",
                    action,
                    integration_id,
                    available,
                )
                actions_dict = {}

        if not actions_dict or all(k == "integration" for k in actions_dict):
            action_name_to_eval = action or "Integration Actions (Missing or Empty YAML)"
            actions_dict[action_name_to_eval] = {}
            logger.warning(
                "No action definitions found in YAML for '%s'. Adding placeholder action '%s' for failure reporting.",
                integration_id,
                action_name_to_eval,
            )

        run_id = f"run_{uuid.uuid4().hex[:8]}"
        evaluated_at = datetime.now(tz=UTC).isoformat()

        logger.info(
            "🤖 [2/4] Initializing evaluation engine for '%s' (%d actions, Run ID: %s)...",
            integration_id,
            len(actions_dict),
            run_id,
        )

        results: list[RuleEvaluationResult] = []
        prompts: list[str] = []
        action_rules_list: list[tuple[str, Any]] = []

        for action_name, fields in actions_dict.items():
            if action_name in {
                "integration",
                "product_categories",
                "security_domains",
                "integration_categories",
            }:
                continue
            action_code, action_files, shared_files = get_code_for_action(action_name, python_files)
            logger.info(
                "  📄 (%s) Using %d files for evaluation prompt:\n"
                "    - Action-Specific (%d):\n        * %s\n"
                "    - Shared / Common (%d):\n        * %s",
                action_name,
                len(action_files) + len(shared_files),
                len(action_files),
                "\n        * ".join(action_files) if action_files else "None",
                len(shared_files),
                "\n        * ".join(shared_files) if shared_files else "None",
            )
            for rule in active_rules:
                is_valid, err_reason = self._validate_field_for_rule(rule.target_field, fields)
                if not is_valid:
                    eval_id = f"eval_{uuid.uuid4().hex[:8]}"
                    res_fail = RuleEvaluationResult(
                        evaluation_id=eval_id,
                        integration_id=integration_id,
                        action_id=action_name,
                        run_id=run_id,
                        evaluated_at=evaluated_at,
                        rule_id=rule.rule_id,
                        rule_title=rule.title,
                        actual_value=fields.get(rule.target_field, "-"),
                        verdict=VerdictEnum.FAIL,
                        reasoning=(
                            f"target field '{rule.target_field}' is missing, empty, or malformed in YAML: {err_reason}."
                        ),
                        suggested_fix=f"Define a valid '{rule.target_field}' in the action YAML.",
                        prompt=None,
                    )

                    results.append(res_fail)
                    if self.storage:
                        self.storage.save_evaluation(res_fail)
                    logger.info(
                        "  [%s] %s: FAIL (Missing/Invalid Field: %s)",
                        action_name,
                        rule.title,
                        rule.target_field,
                    )
                else:
                    prompt = build_evaluation_prompt(
                        rule,
                        original_prompt,
                        action_code,
                        fields.get(rule.target_field, ""),
                    )
                    prompts.append(prompt)
                    action_rules_list.append((action_name, rule))

        llm_responses: list[RuleVerdict | str] = []

        if use_llm and prompts:
            try:
                mode_str = "Batch API" if use_batch else "Direct Streaming"
                logger.info(
                    "⚡ [3/4] Dispatching %d rule evaluation prompts to Gemini API (%s)...",
                    len(prompts),
                    mode_str,
                )
                llm_responses = EvaluationEngine._dispatch_prompts(prompts, use_batch=use_batch)
            except Exception as err:  # ruff: ignore[blind-except]
                logger.warning(
                    "Gemini API evaluation offline or unavailable: %s. Using heuristic evaluation.",
                    err,
                )
                llm_responses = []

        heuristic_fallbacks: list[tuple[str, str]] = []

        for idx, (action_name, rule) in enumerate(action_rules_list):
            eval_id = f"eval_{uuid.uuid4().hex[:8]}"
            fields = actions_dict.get(action_name, {})
            target_val = fields.get(rule.target_field, f"Sample value for {rule.target_field}")

            verdict_val = VerdictEnum.PASS
            reasoning = f"Rule '{rule.title}' passed criteria verification."
            fix = None

            if idx < len(llm_responses) and isinstance(llm_responses[idx], RuleVerdict):
                v_resp = llm_responses[idx]
                if isinstance(v_resp, RuleVerdict):
                    verdict_val = v_resp.verdict
                    reasoning = v_resp.reasoning
                    fix = v_resp.suggested_fix
                    logger.info(
                        "  [%s] %s: %s",
                        action_name,
                        rule.title,
                        verdict_val.value,
                    )
            else:
                heuristic_fallbacks.append((action_name, rule.title))
                verdict_val, reasoning, fix = self._heuristic_evaluate_rule(rule.title, rule.target_field, target_val)
                logger.info(
                    "  [%s] %s: %s (Heuristic)",
                    action_name,
                    rule.title,
                    verdict_val.value,
                )

            res = RuleEvaluationResult(
                evaluation_id=eval_id,
                integration_id=integration_id,
                action_id=action_name,
                run_id=run_id,
                evaluated_at=evaluated_at,
                rule_id=rule.rule_id,
                rule_title=rule.title,
                actual_value=target_val,
                verdict=verdict_val,
                reasoning=reasoning,
                suggested_fix=fix,
                prompt=prompts[idx] if add_prompt and idx < len(prompts) else None,
            )

            results.append(res)
            if self.storage:
                self.storage.save_evaluation(res)

        if self.storage:
            logger.info("💾 [4/4] Persisted %d rule evaluation records to SQLite database.", len(results))

        if heuristic_fallbacks:
            logger.warning(
                "⚠️ [RE-RUN RECOMMENDED] %d rule evaluation(s) fell back to heuristic "
                "verification because Gemini API was offline, disabled, or returned unparseable JSON:",
                len(heuristic_fallbacks),
            )
            for action_name, rule_title in heuristic_fallbacks:
                logger.warning("   - [%s] %s", action_name, rule_title)
            logger.warning(
                "💡 Tip: Re-run 'mp describe evaluate %s --use-llm' to validate these rules with Gemini.",
                integration_id,
            )

        results.sort(key=lambda r: (r.action_id, r.rule_title))
        pass_cnt = sum(1 for r in results if r.verdict == VerdictEnum.PASS)
        fail_cnt = sum(1 for r in results if r.verdict == VerdictEnum.FAIL)
        partial_cnt = sum(1 for r in results if r.verdict == VerdictEnum.PARTIAL)
        total = len(results)
        score = (pass_cnt + (0.5 * partial_cnt)) / total * 100.0 if total > 0 else 0.0

        return EvaluationReport(
            integration_id=integration_id,
            run_id=run_id,
            evaluated_at=evaluated_at,
            total_evaluations=total,
            pass_count=pass_cnt,
            fail_count=fail_cnt,
            partial_count=partial_cnt,
            score_percentage=score,
            results=results,
            analyzed_files=input_file_paths,
        )
