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

import pathlib
from dataclasses import dataclass

import yaml


@dataclass(frozen=True)
class EvaluationRule:
    """Definition of an evaluation rule."""

    title: str
    target_field: str
    criteria: str


def load_rules_from_yaml(
    ruleset_path: pathlib.Path | None = None,
) -> list[EvaluationRule]:
    """Load evaluation rules from an external YAML file.

    Args:
        ruleset_path: Path to the YAML file containing rule definitions. If None,
            loads the default ruleset packaged with the module.

    Returns:
        List of EvaluationRule objects.

    Raises:
        FileNotFoundError: If the specified ruleset file does not exist.
        TypeError: If the ruleset file is not a list.
        ValueError: If the ruleset file is malformed.

    """
    if ruleset_path is None:
        ruleset_path = pathlib.Path(__file__).parent / "default_rules.yaml"

    if not ruleset_path.exists():
        msg = f"Evaluation ruleset file not found: {ruleset_path}"
        raise FileNotFoundError(msg)

    content = ruleset_path.read_text(encoding="utf-8")
    data = yaml.safe_load(content)
    if not isinstance(data, list):
        msg = f"Ruleset YAML {ruleset_path} must contain a list of rules."
        raise TypeError(msg)

    rules: list[EvaluationRule] = []
    for item in data:
        if (
            not isinstance(item, dict)
            or not item.get("title")
            or not item.get("target_field")
            or not item.get("criteria")
        ):
            continue
        rule = EvaluationRule(
            title=str(item["title"]).strip(),
            target_field=str(item["target_field"]).strip(),
            criteria=str(item["criteria"]).strip(),
        )
        rules.append(rule)

    if not rules:
        msg = f"No valid rules loaded from {ruleset_path}."
        raise ValueError(msg)

    return rules


EVALUATION_RULES: list[EvaluationRule] = load_rules_from_yaml()


def build_evaluation_prompt(
    rule: EvaluationRule,
    original_prompt: str,
    python_code: str,
    target_field_value: str,
) -> str:
    """Construct XML context prompt for single rule evaluation via Gemini.

    Args:
        rule: The rule to evaluate.
        original_prompt: The prompt used to generate original description.
        python_code: The Python source code of action/integration.
        target_field_value: The target field string/JSON value extracted.

    Returns:
        Formatted evaluation prompt string.

    """
    task_desc = (
        "You are an expert Code Auditor and Data Integrity Judge. "
        "Your sole task is to evaluate the input data against exactly one specific rule. "
        "The <python_script> block includes both the Python implementation scripts "
        "and the action definition (.actiondef/.yaml/.json) files."
    )
    format_desc = (
        "You must output your complete evaluation only as a valid JSON object matching "
        "the schema below. Do not include conversational filler or markdown formatting."
    )
    reasoning_desc = (
        "Provide step-by-step logical justification. "
        "You MUST quote exact code snippets or extracted values supporting your verdict."
    )
    fix_desc = (
        "If verdict is FAIL or PARTIAL, provide exact code or payload modification. "
        "If PASS, set this field to null."
    )

    safe_prompt = original_prompt.replace("</original_prompt>", "&lt;/original_prompt&gt;")
    safe_code = python_code.replace("</python_script>", "&lt;/python_script&gt;")
    safe_val = target_field_value.replace("</target_field_extracted>", "&lt;/target_field_extracted&gt;")

    return f"""<original_prompt>
{safe_prompt}
</original_prompt>

<python_script>
{safe_code}
</python_script>

<target_field_extracted>
Field Name: {rule.target_field}
{safe_val}
</target_field_extracted>

### YOUR EVALUATION TASK

{task_desc}

You must ignore all other aspects of the script and target field except for the rule defined below.

---

#### THE SINGLE RULE TO EVALUATE

Rule: {rule.title}
Evaluation Criteria:
{rule.criteria}

---

#### EVALUATION INSTRUCTIONS

1. Analyze the Input: Carefully inspect the <python_script> and the extracted data in <target_field_extracted>.
2. Find the Evidence: Search for the exact line(s) of code, string patterns, or JSON keys relevant to the rule.
3. Formulate the Verdict:
   - PASS: The code and extracted data strictly and fully adhere to the rule.
   - FAIL: There is a clear violation of the rule.
   - PARTIAL: The rule is mostly followed, but there is an edge case, formatting oversight, or potential risk.

---

#### OUTPUT FORMAT

{format_desc}

```json
{{
  "rule_evaluated": "{rule.title}",
  "verdict": "PASS | FAIL | PARTIAL",
  "reasoning": "{reasoning_desc}",
  "suggested_fix": "{fix_desc}"
}}
```
"""
