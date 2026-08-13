import json
import re
from collections import defaultdict
import pathlib

def parse_ledger():
    ledger_path = "packages/mp/agent_reports/agent_metrics_ledger.jsonl"
    with open(ledger_path, "r") as f:
        lines = f.readlines()
        
    records = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            # Fix corrupted prefix if present (find first '{')
            start_idx = line.find('{')
            if start_idx != -1:
                line = line[start_idx:]
                records.append(json.loads(line))
        except Exception as e:
            print(f"Skipping line due to error: {e}")
            
    # rule_id -> { "count": int, "actions": set, "failures": list }
    rules = defaultdict(lambda: {"count": 0, "actions": set(), "failures": []})
    total_actions = len(records)
    
    for record in records:
        feedbacks = record.get("validation_feedbacks", [])
        if not feedbacks:
            continue
            
        action_name = record["action"]
        
        for fb in feedbacks:
            detected_rules = []
            
            # Heuristic 1: "Check \d+: Failed" or "Rule \d+"
            check_matches = re.finditer(r'(?:Check|Rule) (\d+):\s*?(?:Failed|No)', fb, re.IGNORECASE)
            for m in check_matches:
                detected_rules.append(m.group(1))
                
            # Heuristic 2: "7. Some text... No."
            numbered_matches = re.finditer(r'(\d+)\.\s*([^0-9]{10,400}?)(?:No|Failed|False)', fb, re.IGNORECASE | re.DOTALL)
            for m in numbered_matches:
                detected_rules.append(m.group(1))
            
            # Deduplicate
            detected_rules = list(set(detected_rules))
            
            if not detected_rules:
                # If we couldn't parse the number, group as Uncategorized
                detected_rules = ["Uncategorized"]
                
            for r in detected_rules:
                rules[r]["count"] += 1
                rules[r]["actions"].add(action_name)
                rules[r]["failures"].append({
                    "action": action_name,
                    "integration": record["integration"],
                    "feedback": fb
                })
                
    return rules, total_actions

def generate_markdown(rules, total_actions):
    md = [
        "# Agent Validation Metrics Aggregation Report",
        f"**Total Generation Runs:** {total_actions}\n",
        "## Failure Summary by Rule",
        "| Rule/Check ID | Total Failures | % of Runs Affected | Affected Actions |",
        "| :--- | :--- | :--- | :--- |"
    ]
    
    sorted_rules = sorted(rules.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999)
    
    for rule_id, data in sorted_rules:
        pct = (len(data['actions']) / total_actions) * 100 if total_actions > 0 else 0
        actions_str = ", ".join(data['actions'])
        md.append(f"| Rule/Check {rule_id} | {data['count']} | {pct:.1f}% | {actions_str} |")
        
    md.append("\n## Detailed Failures by Rule")
    
    for rule_id, data in sorted_rules:
        md.append(f"### Rule/Check {rule_id}")
        for failure in data["failures"]:
            md.append(f"**Action:** `{failure['action']}`")
            md.append("```text\n" + failure['feedback'].strip() + "\n```")
            md.append("---")
            
    return "\n".join(md)

rules, total_actions = parse_ledger()
md_content = generate_markdown(rules, total_actions)

with open("/usr/local/google/home/hmaor/.gemini/jetski/brain/83d7cbff-496a-42a2-8a9b-a02a9fba52b9/validation_aggregation_report.md", "w") as f:
    f.write(md_content)

print("Generated.")
