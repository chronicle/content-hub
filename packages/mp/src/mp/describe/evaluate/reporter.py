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

import html
import json
from typing import TYPE_CHECKING

from .models import EvaluationReport, RuleEvaluationResult, VerdictEnum

if TYPE_CHECKING:
    from pathlib import Path


class EvaluationReporter:
    """Reporter engine for mp describe evaluate reports."""

    @staticmethod
    def render_markdown(report: EvaluationReport) -> str:
        """Render evaluation report in GitHub Flavored Markdown.

        Args:
            report: EvaluationReport object.

        Returns:
            Markdown formatted report string.

        """
        counts = f"{report.pass_count} PASS | {report.fail_count} FAIL | {report.partial_count} PARTIAL"
        md_lines: list[str] = [
            f"# Evaluation Report: `{report.integration_id}`",
            "",
            f"- **Run ID**: `{report.run_id}`",
            f"- **Evaluated At**: `{report.evaluated_at}`",
            f"- **Overall Quality Score**: `{report.score_percentage:.1f}%`",
            f"- **Total Rules Evaluated**: `{report.total_evaluations}`",
            f"- **Pass / Fail / Partial**: `{counts}`",
            "",
            "## Input Files Analyzed",
            "",
        ]

        if report.analyzed_files:
            md_lines.extend([f"- `{filepath}`" for filepath in report.analyzed_files])
        else:
            md_lines.append("_No input files specified._")

        actions_seen: list[str] = []
        results_by_action: dict[str, list[RuleEvaluationResult]] = {}
        for res in report.results:
            if res.action_id not in results_by_action:
                actions_seen.append(res.action_id)
                results_by_action[res.action_id] = []
            results_by_action[res.action_id].append(res)

        has_prompt = any(r.prompt for r in report.results)

        for act_id in actions_seen:
            results_by_action[act_id].sort(key=lambda r: r.rule_title)
            heading = (
                "## Rule Verdicts & Findings"
                if act_id == "all_actions" and len(actions_seen) == 1
                else f"## Action: `{act_id}`"
            )
            if has_prompt:
                md_lines.extend([
                    "",
                    heading,
                    "",
                    "| Title | Actual Value | Verdict | Reasoning | Suggested Fix | Prompt |",
                    "| :--- | :--- | :---: | :--- | :--- | :--- |",
                ])
            else:
                md_lines.extend([
                    "",
                    heading,
                    "",
                    "| Title | Actual Value | Verdict | Reasoning | Suggested Fix |",
                    "| :--- | :--- | :---: | :--- | :--- |",
                ])

            for res in results_by_action[act_id]:
                verdict_badge = {
                    VerdictEnum.PASS: "🟢 PASS",
                    VerdictEnum.FAIL: "🔴 FAIL",
                    VerdictEnum.PARTIAL: "🟡 PARTIAL",
                }[res.verdict]

                actual_clean = (res.actual_value or "-").replace("\n", "<br/>").replace("|", "\\|")
                fix_text = res.suggested_fix or "-"
                reasoning_clean = res.reasoning.replace("\n", "<br/>").replace("|", "\\|")
                fix_clean = fix_text.replace("\n", "<br/>").replace("|", "\\|")

                prompt_col = ""
                if has_prompt:
                    if res.prompt:
                        p_clean = html.escape(res.prompt).replace("\n", "<br/>").replace("|", "\\|")
                        prompt_col = f" | <details><summary>Show Prompt</summary><code>{p_clean}</code></details>"
                    else:
                        prompt_col = " | -"

                row_str = (
                    f"| **{res.rule_title}** | {actual_clean} | "
                    f"{verdict_badge} | {reasoning_clean} | {fix_clean}{prompt_col} |"
                )
                md_lines.append(row_str)

        md_lines.append("")
        return "\n".join(md_lines)

    @staticmethod
    def render_json(report: EvaluationReport) -> str:
        """Render evaluation report as JSON string.

        Args:
            report: EvaluationReport object.

        Returns:
            Formatted JSON string.

        """
        return json.dumps(report.to_dict(), indent=2)

    @staticmethod
    def _render_prompt_modal_td(res: RuleEvaluationResult, *, has_prompt: bool, title_esc: str) -> str:
        """Render table data cell with prompt modal if present.

        Args:
            res: Evaluation result object.
            has_prompt: Whether any result has prompt text.
            title_esc: HTML escaped rule title.

        Returns:
            HTML string for table cell.

        """
        if not has_prompt:
            return ""
        if not res.prompt:
            return "<td>-</td>"
        prompt_esc = html.escape(res.prompt)
        modal_id = f"prompt_modal_{res.evaluation_id}"
        onclick_hide = f"document.getElementById('{modal_id}').style.display='none'"
        onclick_show = f"document.getElementById('{modal_id}').style.display='block'"
        pre_style = (
            "white-space:pre-wrap;background:#f8f9fa;padding:15px;"
            "border:1px solid #ccc;border-radius:4px;"
            "max-height:70vh;overflow:auto;"
        )
        return (
            f'<td><button onclick="{onclick_show}">Show/Hide Prompt</button>'
            f'<div id="{modal_id}" class="modal" '
            "onclick=\"if(event.target===this)this.style.display='none'\">"
            "<div class='modal-content'>"
            f'<span class="close-btn" onclick="{onclick_hide}">&times;</span>'
            f"<h3>Prompt for Rule: {title_esc}</h3>"
            f"<pre style='{pre_style}'>{prompt_esc}</pre>"
            "</div></div></td>"
        )

    @staticmethod
    def _render_html_action_table(
        act_id: str,
        results: list[RuleEvaluationResult],
        *,
        has_prompt: bool,
        single_action: bool,
    ) -> str:
        """Render HTML table for a single action's evaluation results.

        Args:
            act_id: Action name or ID.
            results: List of evaluation results for this action.
            has_prompt: Whether any result has prompt text.
            single_action: Whether only one action was evaluated.

        Returns:
            HTML string representation of the table.

        """
        results.sort(key=lambda r: r.rule_title)
        heading = (
            "Rule Verdicts & Findings"
            if act_id == "all_actions" and single_action
            else f"Action: {html.escape(act_id)}"
        )
        prompt_header = "<th>Prompt</th>" if has_prompt else ""
        rows: list[str] = []
        for res in results:
            if res.verdict == VerdictEnum.PASS:
                color = "#27ae60"
            elif res.verdict == VerdictEnum.FAIL:
                color = "#e74c3c"
            else:
                color = "#f39c12"

            actual_esc = html.escape(res.actual_value) if res.actual_value else "-"
            actual_html = f"<code>{actual_esc}</code>" if res.actual_value else "-"
            fix_esc = html.escape(res.suggested_fix) if res.suggested_fix else "None"
            fix = f"<code>{fix_esc}</code>" if res.suggested_fix else "None"
            title_esc = html.escape(res.rule_title)
            reason_esc = html.escape(res.reasoning)
            prompt_td = EvaluationReporter._render_prompt_modal_td(res, has_prompt=has_prompt, title_esc=title_esc)

            rows.append(
                f"<tr><td>{title_esc}</td>"
                f"<td>{actual_html}</td>"
                f"<td style='color:{color};font-weight:bold;'>{res.verdict.value}</td>"
                f"<td>{reason_esc}</td><td>{fix}</td>{prompt_td}</tr>"
            )
        return f"""<h2>{heading}</h2>
    <table>
        <thead>
            <tr>
                <th>Title</th><th>Actual Value</th>
                <th>Verdict</th><th>Reasoning</th><th>Suggested Fix</th>{prompt_header}
            </tr>
        </thead>
        <tbody>
            {"".join(rows)}
        </tbody>
    </table>"""

    @staticmethod
    def render_html(report: EvaluationReport) -> str:
        """Render evaluation report as HTML page.

        Args:
            report: EvaluationReport object.

        Returns:
            HTML string representation.

        """
        actions_seen: list[str] = []
        results_by_action: dict[str, list[RuleEvaluationResult]] = {}
        for res in report.results:
            if res.action_id not in results_by_action:
                actions_seen.append(res.action_id)
                results_by_action[res.action_id] = []
            results_by_action[res.action_id].append(res)

        has_prompt = any(r.prompt for r in report.results)
        single_action = len(actions_seen) == 1
        tables_html_parts = [
            EvaluationReporter._render_html_action_table(
                act_id,
                results_by_action[act_id],
                has_prompt=has_prompt,
                single_action=single_action,
            )
            for act_id in actions_seen
        ]

        files_items = [f"<li><code>{html.escape(f)}</code></li>" for f in report.analyzed_files]
        files_html = "".join(files_items) or "<li>None</li>"

        integration_id_esc = html.escape(report.integration_id)
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>Evaluation Report - {integration_id_esc}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #2c3e50; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        ul.file-list {{ background: #f8f9fa; padding: 15px; border-radius: 5px; }}
        .modal {{
            display: none; position: fixed; z-index: 1000; left: 0; top: 0;
            width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.5);
        }}
        .modal-content {{
            background-color: #fff; margin: 5% auto; padding: 20px;
            border: 1px solid #888; width: 80%; max-height: 80vh; overflow-y: auto;
            border-radius: 5px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            position: relative;
        }}
        .close-btn {{
            color: #aaa; float: right; font-size: 28px; font-weight: bold; cursor: pointer;
        }}
        .close-btn:hover, .close-btn:focus {{
            color: #000; text-decoration: none;
        }}
    </style>
</head>
<body>
    <h1>Evaluation Report: {integration_id_esc}</h1>
    <p><strong>Run ID:</strong> {report.run_id} | <strong>Score:</strong> {report.score_percentage:.1f}%</p>
    <p><strong>Verdicts:</strong> {report.pass_count} PASS, {report.fail_count} FAIL, {report.partial_count} PARTIAL</p>

    <h2>Input Files Analyzed</h2>
    <ul class="file-list">
        {files_html}
    </ul>

    {"".join(tables_html_parts)}
</body>
</html>"""

    @classmethod
    def export_report(
        cls,
        report: EvaluationReport,
        export_format: str,
        output_path: Path | None = None,
    ) -> str:
        """Render and optionally export evaluation report to file.

        Args:
            report: EvaluationReport object.
            export_format: Format string ('markdown', 'json', 'html').
            output_path: Optional output file Path.

        Returns:
            Rendered report string.

        Raises:
            ValueError: If export_format is not one of 'markdown', 'json', or 'html'.

        """
        fmt = export_format.lower()
        if fmt == "json":
            rendered = cls.render_json(report)
        elif fmt == "html":
            rendered = cls.render_html(report)
        elif fmt in {"markdown", "md"}:
            rendered = cls.render_markdown(report)
        else:
            msg = f"Unsupported export format '{export_format}'. Must be one of: 'markdown', 'json', 'html'."
            raise ValueError(msg)

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding="utf-8")

        return rendered
