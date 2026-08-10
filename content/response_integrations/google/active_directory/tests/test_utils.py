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
import unittest
from typing import Any
from core.utils import prevent_reverting_properties


class MockEntity:
    def __init__(
        self,
        is_pivot: bool | None = None,
        is_attacker: bool | None = None,
        is_vulnerable: bool | None = None,
        attacker: bool | None = None,
        additional_properties: dict[str, Any] | None = None,
    ):
        if is_pivot is not None:
            self.is_pivot = is_pivot
        if is_attacker is not None:
            self.is_attacker = is_attacker
        if is_vulnerable is not None:
            self.is_vulnerable = is_vulnerable
        if attacker is not None:
            self.attacker = attacker
        self.additional_properties = additional_properties or {}

    def to_dict(self) -> dict[str, Any]:
        d = {}
        if hasattr(self, "is_pivot"):
            d["is_pivot"] = self.is_pivot
            d["IsPivot"] = self.is_pivot
        if hasattr(self, "is_attacker"):
            d["is_attacker"] = self.is_attacker
            d["IsAttacker"] = self.is_attacker
        if hasattr(self, "attacker"):
            d["attacker"] = self.attacker
            d["IsAttacker"] = self.attacker
        if hasattr(self, "is_vulnerable"):
            d["is_vulnerable"] = self.is_vulnerable
            d["IsVulnerable"] = self.is_vulnerable

        d["additional_properties"] = self.additional_properties.copy()
        return d


class TestUtils(unittest.TestCase):
    def test_prevent_reverting_properties_no_to_dict(self):
        # Entity with no to_dict method
        class NoToDictEntity:
            pass

        entity = NoToDictEntity()
        prevent_reverting_properties(entity)
        self.assertFalse(hasattr(entity, "to_dict"))

    def test_prevent_reverting_properties_all_true(self):
        # If all properties are True locally, all should be stripped from output
        entity = MockEntity(
            is_pivot=True,
            is_attacker=True,
            is_vulnerable=True,
            additional_properties={
                "IsPivot": True,
                "IsAttacker": True,
                "IsVulnerable": True,
            },
        )
        prevent_reverting_properties(entity)
        d = entity.to_dict()

        self.assertNotIn("is_pivot", d)
        self.assertNotIn("IsPivot", d)
        self.assertNotIn("is_attacker", d)
        self.assertNotIn("IsAttacker", d)
        self.assertNotIn("is_vulnerable", d)
        self.assertNotIn("IsVulnerable", d)

        add_props = d.get("additional_properties")
        self.assertNotIn("IsPivot", add_props)
        self.assertNotIn("IsAttacker", add_props)
        self.assertNotIn("IsVulnerable", add_props)

    def test_prevent_reverting_properties_all_false_and_unset(self):
        # If all properties are False, no monkeypatching is applied and they are preserved
        entity = MockEntity(
            is_pivot=False,
            is_attacker=False,
            is_vulnerable=False,
            additional_properties={
                "IsPivot": False,
                "IsAttacker": False,
                "IsVulnerable": False,
            },
        )
        prevent_reverting_properties(entity)
        d = entity.to_dict()

        self.assertIn("is_pivot", d)
        self.assertIn("IsPivot", d)
        self.assertIn("is_attacker", d)
        self.assertIn("IsAttacker", d)
        self.assertIn("is_vulnerable", d)
        self.assertIn("IsVulnerable", d)

        add_props = d.get("additional_properties")
        self.assertIn("IsPivot", add_props)
        self.assertIn("IsAttacker", add_props)
        self.assertIn("IsVulnerable", add_props)

    def test_prevent_reverting_properties_mixed(self):
        # Only true properties (IsPivot) should be stripped
        entity = MockEntity(
            is_pivot=True,
            is_attacker=False,
            is_vulnerable=False,
            additional_properties={
                "IsPivot": "true",
                "IsAttacker": False,
                "IsVulnerable": "false",
            },
        )
        prevent_reverting_properties(entity)
        d = entity.to_dict()

        self.assertNotIn("is_pivot", d)
        self.assertNotIn("IsPivot", d)
        self.assertIn("is_attacker", d)
        self.assertIn("IsAttacker", d)
        self.assertIn("is_vulnerable", d)
        self.assertIn("IsVulnerable", d)

        add_props = d.get("additional_properties")
        self.assertNotIn("IsPivot", add_props)
        self.assertIn("IsAttacker", add_props)
        self.assertIn("IsVulnerable", add_props)


if __name__ == "__main__":
    unittest.main()
