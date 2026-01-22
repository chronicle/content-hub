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

from pathlib import Path

import pytest
import yaml

from mp.core.exceptions import NonFatalValidationError
from mp.validate.pre_build_validation.integrations.fields_validation import (
    FieldsValidation,
)


def test_fields_validation_run_valid(temp_integration: Path) -> None:
    FieldsValidation.run(temp_integration)


def test_fields_validation_invalid_integration_name(temp_integration: Path) -> None:
    definition_path = temp_integration / "definition.yaml"
    with Path(definition_path).open(encoding="utf-8") as f:
        definition = yaml.safe_load(f)

    invalid_name = "Invalid Name!"
    definition["name"] = invalid_name

    with Path(definition_path).open("w", encoding="utf-8") as f:
        yaml.dump(definition, f)

    with pytest.raises(NonFatalValidationError) as excinfo:
        FieldsValidation.run(temp_integration)

    assert "Integration name" in str(excinfo.value)
    assert invalid_name in str(excinfo.value)


def test_fields_validation_invalid_action_name(temp_integration: Path) -> None:
    action_path = temp_integration / "actions" / "ping.yaml"
    with Path(action_path).open(encoding="utf-8") as f:
        action = yaml.safe_load(f)

    invalid_name = "Ping_"
    action["name"] = invalid_name

    with Path(action_path).open("w", encoding="utf-8") as f:
        yaml.dump(action, f)

    with pytest.raises(NonFatalValidationError) as excinfo:
        FieldsValidation.run(temp_integration)

    assert "Action name" in str(excinfo.value)
    assert invalid_name in str(excinfo.value)


def test_fields_validation_invalid_action_parameter_name(temp_integration: Path) -> None:
    action_path = temp_integration / "actions" / "ping.yaml"
    with Path(action_path).open(encoding="utf-8") as f:
        action = yaml.safe_load(f)

    invalid_name = "Host!"
    action["parameters"][0]["name"] = invalid_name

    with Path(action_path).open("w", encoding="utf-8") as f:
        yaml.dump(action, f)

    with pytest.raises(NonFatalValidationError) as excinfo:
        FieldsValidation.run(temp_integration)

    assert "Action Parameter name" in str(excinfo.value)
    assert invalid_name in str(excinfo.value)


def test_fields_validation_invalid_connector_name(temp_integration: Path) -> None:
    connector_path = temp_integration / "connectors" / "connector.yaml"
    with Path(connector_path).open(encoding="utf-8") as f:
        connector = yaml.safe_load(f)

    invalid_name = "Mock_Connector"
    connector["name"] = invalid_name

    with Path(connector_path).open("w", encoding="utf-8") as f:
        yaml.dump(connector, f)

    with pytest.raises(NonFatalValidationError) as excinfo:
        FieldsValidation.run(temp_integration)

    assert "Connector name" in str(excinfo.value)
    assert invalid_name in str(excinfo.value)


def test_fields_validation_invalid_connector_parameter_name(temp_integration: Path) -> None:
    connector_path = temp_integration / "connectors" / "connector.yaml"
    with Path(connector_path).open(encoding="utf-8") as f:
        connector = yaml.safe_load(f)

    invalid_name = "Param!"
    connector["parameters"] = [
        {
            "name": invalid_name,
            "description": "A parameter with an invalid name",
            "type": "string",
            "is_mandatory": False,
            "is_advanced": False,
            "mode": "script",
            "default_value": "",
        }
    ]

    with Path(connector_path).open("w", encoding="utf-8") as f:
        yaml.dump(connector, f)

    with pytest.raises(NonFatalValidationError) as excinfo:
        FieldsValidation.run(temp_integration)

    assert "Connector Parameter name" in str(excinfo.value)
    assert invalid_name in str(excinfo.value)


def test_fields_validation_invalid_job_name(temp_integration: Path) -> None:
    job_path = temp_integration / "jobs" / "job.yaml"
    with Path(job_path).open(encoding="utf-8") as f:
        job = yaml.safe_load(f)

    invalid_name = "Mock Job!"
    job["name"] = invalid_name

    with Path(job_path).open("w", encoding="utf-8") as f:
        yaml.dump(job, f)

    with pytest.raises(NonFatalValidationError) as excinfo:
        FieldsValidation.run(temp_integration)

    assert "Job name" in str(excinfo.value)
    assert invalid_name in str(excinfo.value)


def test_fields_validation_invalid_job_parameter_name(temp_integration: Path) -> None:
    job_path = temp_integration / "jobs" / "job.yaml"
    with Path(job_path).open(encoding="utf-8") as f:
        job = yaml.safe_load(f)

    invalid_name = "Mock Job Parameter!"
    job["parameters"][0]["name"] = invalid_name

    with Path(job_path).open("w", encoding="utf-8") as f:
        yaml.dump(job, f)

    with pytest.raises(NonFatalValidationError) as excinfo:
        FieldsValidation.run(temp_integration)

    assert "Job Parameter name" in str(excinfo.value)
    assert invalid_name in str(excinfo.value)
