from pathlib import Path
import json
import sys

# Target directory to walk
target_dir = Path("content/parsers/third_party")
output_dir = Path("content/parsers/third_party")

# Subdirectories for community and partner
community_dir = target_dir / "community"
partner_dir = target_dir / "partner"

def generate_index_for_subdir(sub_dir: Path, output_json_name: str, output_md_name: str, source_type: str):
    entries = []
    
    # If the sub-directory doesn't exist, skip it
    if not sub_dir.exists():
        print(f"WARNING: Subdirectory {sub_dir} does not exist. Skipping.")
        return
        
    # Recursively find all metadata.json files using rglob
    for metadata_path in sub_dir.rglob("metadata.json"):
        parser_root = metadata_path.parent
        
        # Locate configuration file (.conf) using glob
        conf_files = list(parser_root.glob("*.conf"))
        if not conf_files:
            continue
        config_path = conf_files[0]
        
        # Read metadata.json
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception as e:
            print(f"WARNING: Failed to parse JSON in {metadata_path}: {e}", file=sys.stderr)
            continue
            
        # Extract log type
        log_type = meta.get("log_type") or meta.get("logtype") or meta.get("logType")
        if not log_type or not log_type.strip():
            print(f"WARNING: Missing log type in {metadata_path}", file=sys.stderr)
            continue
            
        entries.append({
            "log_type": log_type.strip().upper(),
            "config_path": config_path.as_posix(),
            "metadata_path": metadata_path.as_posix(),
            "vendor": meta.get("vendor", ""),
            "product": meta.get("product", ""),
            "source": source_type
        })
        
    # Sort entries alphabetically by log type
    entries.sort(key=lambda x: x["log_type"])
    
    # Write JSON index file
    json_path = output_dir / output_json_name
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)
        print(f"Successfully generated {json_path}")
    except Exception as e:
        print(f"ERROR: Failed to write {json_path}: {e}", file=sys.stderr)
        sys.exit(1)
        
    # Write Markdown index file
    md_path = output_dir / output_md_name
    md_lines = [
        f"# {source_type.title()} Parser Index",
        "",
        "| Log Type | Config File |",
        "| :--- | :--- |"
    ]
    for entry in entries:
        filename = Path(entry['config_path']).name
        md_lines.append(f"| {entry['log_type']} | [{filename}]({entry['config_path']}) |")
        
    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines) + "\n")
        print(f"Successfully generated {md_path}")
    except Exception as e:
        print(f"ERROR: Failed to write {md_path}: {e}", file=sys.stderr)
        sys.exit(1)

# Generate Community Index
generate_index_for_subdir(
    sub_dir=community_dir,
    output_json_name="COMMUNITY_INDEX.json",
    output_md_name="COMMUNITY_INDEX.md",
    source_type="COMMUNITY"
)

# Generate Partner Index
generate_index_for_subdir(
    sub_dir=partner_dir,
    output_json_name="PARTNER_INDEX.json",
    output_md_name="PARTNER_INDEX.md",
    source_type="PARTNER"
)

