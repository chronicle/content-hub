#!/usr/bin/env python3
"""Convert definition.yaml to Integration-Torq.def JSON format for ZIP packaging."""

import json
import pathlib
import sys
from typing import Any

import yaml


def convert_yaml_to_json(yaml_path: pathlib.Path, output_path: pathlib.Path) -> None:
    """Convert definition.yaml to Integration-identifier.def JSON format."""
    with open(yaml_path, "r", encoding="utf-8") as f:
        yaml_data: dict[str, Any] = yaml.safe_load(f)

    identifier: str = yaml_data.get("integration_identifier") or yaml_data.get("identifier", "Torq")
    
    # Convert YAML structure to JSON format expected by the system
    json_data: dict[str, Any] = {
        "Identifier": identifier,
        "DisplayName": yaml_data.get("name", identifier),
        "Version": yaml_data.get("version", "1.0"),
        "PythonVersion": 3,
        "Description": yaml_data.get("description", ""),
        "IsCustom": True,  # Set to True for third_party integrations
    }

    # Handle parameters/configuration
    params = yaml_data.get("parameters") or yaml_data.get("configuration", [])
    json_params = []
    for param in params:
        json_param = {
            "Name": param["name"],
            "Type": param["type"],
            "IsMandatory": param.get("is_mandatory", False),
        }
        if "default_value" in param:
            json_param["DefaultValue"] = param["default_value"]
        if "description" in param:
            json_param["Description"] = param["description"]
        json_params.append(json_param)

    json_data["IntegrationProperties"] = json_params

    # Handle categories
    if "categories" in yaml_data:
        json_data["Categories"] = yaml_data["categories"]

    # Handle documentation link if present
    if "documentation_link" in yaml_data:
        json_data["DocumentationLink"] = yaml_data["documentation_link"]

    # Write JSON file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=4, sort_keys=True)

    print(f"✓ Converted {yaml_path.name} to {output_path.name}")
    print(f"  Identifier: {identifier}")
    print(f"  Version: {json_data['Version']}")
    print(f"  Parameters: {len(json_params)}")


if __name__ == "__main__":
    script_dir = pathlib.Path(__file__).parent
    yaml_file = script_dir / "definition.yaml"
    json_file = script_dir / "Integration-Torq.def"

    if not yaml_file.exists():
        print(f"Error: {yaml_file} not found", file=sys.stderr)
        sys.exit(1)

    convert_yaml_to_json(yaml_file, json_file)
    print(f"\n✓ Created {json_file.name} - ready to include in ZIP")

