import json
import re
from collections import defaultdict
import pathlib
import logging

logger = logging.getLogger(__name__)

def generate_validation_aggregation_report(ledger_path: str = "agent_reports/agent_metrics_ledger.jsonl", output_dir: str = "agent_reports") -> None:
    """Parses the JSONL ledger and generates an aggregated Markdown report."""
    ledger_file = pathlib.Path(ledger_path)
    if not ledger_file.exists():
        logger.warning(f"Ledger file not found at {ledger_path}. Skipping report generation.")
        return

    try:
        with open(ledger_file, "r") as f:
            lines = f.readlines()
            
        records = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Handle corrupted pre-fixes just in case
            start_idx = line.find('{')
            if start_idx != -1:
                line = line[start_idx:]
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        
        # rule_id -> { "count": int, "actions": set, "failures": list }
        rules = defaultdict(lambda: {"count": 0, "actions": set(), "failures": []})
        total_actions = len(records)
        
        if total_actions == 0:
            return
            
        for record in records:
            feedbacks = record.get("validation_feedbacks", [])
            if not feedbacks:
                continue
                
            action_name = record.get("action", "Unknown")
            integration_name = record.get("integration", "Unknown")
            field_name = record.get("field", "Unknown")
            
            for fb in feedbacks:
                detected_rules = []
                
                check_matches = re.finditer(r'(?:Check|Rule) (\d+):\s*?(?:Failed|No)', fb, re.IGNORECASE)
                for m in check_matches:
                    detected_rules.append(m.group(1))
                    
                numbered_matches = re.finditer(r'(\d+)\.\s*([^0-9]{10,400}?)(?:No|Failed|False)', fb, re.IGNORECASE | re.DOTALL)
                for m in numbered_matches:
                    detected_rules.append(m.group(1))
                
                detected_rules = list(set(detected_rules))
                if not detected_rules:
                    detected_rules = ["Uncategorized"]
                    
                for r in detected_rules:
                    rules[r]["count"] += 1
                    rules[r]["actions"].add(f"`{action_name}` ({field_name})")
                    rules[r]["failures"].append({
                        "action": action_name,
                        "field": field_name,
                        "integration": integration_name,
                        "feedback": fb,
                        "first_value": record.get("first_suggested_value", "[Metrics missing from earlier run]"),
                        "final_value": record.get("final_value", "[Metrics missing from earlier run]")
                    })
                    
        # Generate Markdown
        md = [
            "# Agent Validation Metrics Aggregation Report",
            f"**Total Fields Generated (Across Actions):** {total_actions}\n",
            "## Failure Summary by Rule",
            "| Rule/Check ID | Total Failures | % of Runs Affected | Affected Actions |",
            "| :--- | :--- | :--- | :--- |"
        ]
        
        sorted_rules = sorted(rules.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999)
        
        for rule_id, data in sorted_rules:
            pct = (len(data['actions']) / total_actions) * 100 if total_actions > 0 else 0
            actions_str = ", ".join(data['actions'])
            md.append(f"| Rule/Check {rule_id} | {data['count']} | {pct:.1f}% | {actions_str} |")
            
        md.append("")
        md.append("## Detailed Failures by Rule")
        
        for rule_id, data in sorted_rules:
            md.append(f"### Rule/Check {rule_id}")
            for failure in data["failures"]:
                md.append(f"**Integration:** `{failure['integration']}`  ")
                md.append(f"**Action:** `{failure['action']}`  ")
                md.append(f"**Field:** `{failure['field']}`  ")
                md.append("#### Validation Feedback Log:")
                md.append("```text\n" + failure['feedback'].strip() + "\n```")
                md.append("#### Value Before (Failed Draft):")
                md.append("```text\n" + str(failure['first_value']).strip() + "\n```")
                md.append("#### Value After (Corrected Output):")
                md.append("```text\n" + str(failure['final_value']).strip() + "\n```")
                md.append("---")
                
        out_dir = pathlib.Path(output_dir)
        out_dir.mkdir(exist_ok=True, parents=True)
        out_path = out_dir / "validation_aggregation_report.md"
        out_path.write_text("\n".join(md))
        logger.info(f"Successfully generated validation aggregation report at {out_path}")
        
    except Exception as e:
        logger.error(f"Failed to compile validation aggregation report: {e}")
