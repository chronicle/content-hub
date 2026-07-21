import json
import os
import sys

# Target directory to walk
target_dir = "content/parsers/third_party"
output_json_path = "content/parsers/third_party/COMMUNITY_INDEX.json"
output_md_path = "content/parsers/third_party/COMMUNITY_INDEX.md"

entries = []

# Walk directories recursively
for root, dirs, files in os.walk(target_dir):
  # Check if this folder has metadata.json
  if "metadata.json" not in files:
    continue

  metadata_path = os.path.join(root, "metadata.json")

  # Locate configuration file (.conf)
  conf_files = [f for f in files if f.endswith(".conf")]
  if not conf_files:
    continue
  # Pick the first one
  conf_file = conf_files[0]
  config_path = os.path.join(root, conf_file)

  # Read metadata.json
  try:
    with open(metadata_path, "r", encoding="utf-8") as f:
      meta = json.load(f)
  except Exception as e:
    print(
        f"WARNING: Failed to parse JSON in {metadata_path}: {e}",
        file=sys.stderr,
    )
    continue

  # Extract log type (handle naming discrepancies)
  log_type = meta.get("log_type") or meta.get("logtype") or meta.get("logType")
  if not log_type or not log_type.strip():
    print(f"WARNING: Missing log type in {metadata_path}", file=sys.stderr)
    continue

  # Resolve source (COMMUNITY or PARTNER)
  source = "COMMUNITY"
  if (
      "/partner/" in root.lower() or "/partner\\" in root.lower()
  ):  # support both linux/windows path delimiters
    source = "PARTNER"

  entries.append({
      "log_type": log_type.strip().upper(),
      "config_path": config_path.replace(
          os.sep, "/"
      ),  # standardise paths to slash for GitHub/Web
      "metadata_path": metadata_path.replace(os.sep, "/"),
      "vendor": meta.get("vendor", ""),
      "product": meta.get("product", ""),
      "source": source,
  })

# Sort entries alphabetically by log type
entries.sort(key=lambda x: x["log_type"])

# Write COMMUNITY_INDEX.json
try:
  with open(output_json_path, "w", encoding="utf-8") as f:
    json.dump(entries, f, indent=2)
  print(f"Successfully generated {output_json_path}")
except Exception as e:
  print(f"ERROR: Failed to write {output_json_path}: {e}", file=sys.stderr)
  sys.exit(1)

# Write COMMUNITY_INDEX.md
md_lines = [
    "# Community Parser Index",
    "",
    "| Log Type | Config File |",
    "| :--- | :--- |",
]
for entry in entries:
  md_lines.append(
      f"| {entry['log_type']} |"
      f" [{os.path.basename(entry['config_path'])}]({entry['config_path']}) |"
  )

try:
  with open(output_md_path, "w", encoding="utf-8") as f:
    f.write("\n".join(md_lines) + "\n")
  print(f"Successfully generated {output_md_path}")
except Exception as e:
  print(f"ERROR: Failed to write {output_md_path}: {e}", file=sys.stderr)
  sys.exit(1)
