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
import pathlib
import shutil

import pytest

from mp.core import constants
from mp.core.exceptions import FatalValidationError
from mp.validate.utils import (
    get_project_dependency_name,
    load_components_defs,
    load_integration_def,
)


def test_dep_name_simple_equality_specifier() -> None:
    assert get_project_dependency_name("requests==2.25.1") == "requests"


def test_dep_name_greater_than_or_equal_specifier() -> None:
    assert get_project_dependency_name("numpy>=1.20.0") == "numpy"


def test_dep_name_less_than_specifier() -> None:
    assert get_project_dependency_name("pandas<2.0.0") == "pandas"


def test_dep_name_no_specifier() -> None:
    assert get_project_dependency_name("django") == "django"


def test_dep_name_with_hyphen_in_name() -> None:
    assert get_project_dependency_name("my-package>=1.0") == "my-package"


def test_dep_name_with_underscore_in_name() -> None:
    assert get_project_dependency_name("my_package<1.2") == "my_package"


def test_dep_name_with_extras_group() -> None:
    # Assuming the regex correctly includes extras
    assert get_project_dependency_name("requests[security]==2.25.1") == "requests[security]"


def test_dep_name_empty_string() -> None:
    assert get_project_dependency_name("") == ""


def test_dep_name_string_starting_with_specifier() -> None:
    assert get_project_dependency_name(">=1.0") == ""


def _remove_file(file_path: pathlib.Path) -> None:
    """Safely remove a file if it exists."""
    file_path.unlink(missing_ok=True)


class TestLoadIntegrationDef:
    """Tests for the load_integration_def utility function."""

    def test_load_success(self, temp_integration: pathlib.Path) -> None:
        """Test loading a valid definition file."""
        load_integration_def(temp_integration)

    def test_load_file_not_found(self, temp_integration: pathlib.Path) -> None:
        """Test failure when the definition file is missing."""
        _remove_file(temp_integration / constants.DEFINITION_FILE)
        with pytest.raises(FatalValidationError, match="Failed to load integration def file"):
            load_integration_def(temp_integration)


class TestLoadComponentsDefs:
    """Tests for the load_components_defs utility function."""

    def test_load_success(self, temp_integration: pathlib.Path) -> None:
        """Test loading component definitions from existing directories."""
        component_defs = load_components_defs(temp_integration)
        assert constants.ACTIONS_DIR in component_defs
        assert len(component_defs[constants.ACTIONS_DIR]) > 0

    def test_load_missing_dir(self, temp_integration: pathlib.Path) -> None:
        """Test loading when a component directory doesn't exist."""
        actions_dir = temp_integration / constants.ACTIONS_DIR
        shutil.rmtree(actions_dir, ignore_errors=True)

        component_defs = load_components_defs(temp_integration)
        assert constants.ACTIONS_DIR not in component_defs
        assert constants.CONNECTORS_DIR in component_defs

    def test_load_missing_file(self, temp_integration: pathlib.Path) -> None:
        """Test loading when a component file doesn't exist."""
        actions_dir = temp_integration / constants.ACTIONS_DIR
        _remove_file(actions_dir / "ping.yaml")

        component_defs = load_components_defs(temp_integration)
        assert constants.ACTIONS_DIR in component_defs
        assert len(component_defs[constants.ACTIONS_DIR]) == 0
