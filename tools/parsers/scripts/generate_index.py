from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys

# Target directory to walk (assumes script is run from repo root)
target_dir = Path("content/parsers/third_party")
output_dir = Path("content/parsers/third_party")

# Subdirectories for community and partner
community_dir = target_dir / "community"
partner_dir = target_dir / "partner"

def get_latest_commit_info(file_path: Path) -> tuple[str, int | None]:
    """Helper to get the latest Git commit SHA and commit time (epoch) for the file."""
    try:
        # %H is commit hash, %ct is committer date (unix timestamp)
        result = subprocess.run(
            ["git", "log", "-n", "1", "--pretty=format:%H,%ct", "--", file_path.as_posix()],
            capture_output=True,
            text=True,
            check=True
        )
        output = result.stdout.strip()
        if not output:
            return "", None
            
        sha, timestamp_str = output.split(",", 1)
        return sha, int(timestamp_str)
    except subprocess.CalledProcessError:
        return "", None
    except Exception as e:
        print(f"WARNING: Failed to get commit info for {file_path}: {e}", file=sys.stderr)
        return "", None

def generate_index_for_subdir(sub_dir: Path, output_json_name: str, source_type: str):
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
            
        # Get the latest commit ID and time for the config file
        commit_id, commit_time = get_latest_commit_info(config_path)
            
        entries.append({
            "log_type": log_type.strip().upper(),
            "config_path": config_path.as_posix(),
            "metadata_path": metadata_path.as_posix(),
            "vendor": meta.get("vendor", ""),
            "product": meta.get("product", ""),
            "source": source_type,
            "latest_commit_id": commit_id,
            "latest_commit_time": commit_time
        })
        
    # Sort entries alphabetically by log type and config path to prevent ordering variance
    entries.sort(key=lambda x: (x["log_type"], x["config_path"]))
    
    # Write JSON index file
    json_path = output_dir / output_json_name
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)
        print(f"Successfully generated {json_path}")
    except Exception as e:
        print(f"ERROR: Failed to write {json_path}: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    # Generate Community Index
    generate_index_for_subdir(
        sub_dir=community_dir,
        output_json_name="COMMUNITY_INDEX.json",
        source_type="COMMUNITY"
    )

    # Generate Partner Index
    generate_index_for_subdir(
        sub_dir=partner_dir,
        output_json_name="PARTNER_INDEX.json",
        source_type="PARTNER"
    )

if __name__ == "__main__":
    main()
