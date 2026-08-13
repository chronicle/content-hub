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
        additional_properties: dict[str, Any] | None = None,
    ):
        if is_pivot is not None:
            self.is_pivot = is_pivot
        self.additional_properties = additional_properties or {}

    def to_dict(self) -> dict[str, Any]:
        d = {}
        if hasattr(self, "is_pivot"):
            d["is_pivot"] = self.is_pivot
            d["IsPivot"] = self.is_pivot
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

    def test_prevent_reverting_properties_pivot_true(self):
        # If is_pivot is True, it should be stripped from the payload (not modify/overwrite)
        entity = MockEntity(
            is_pivot=True,
            additional_properties={"IsPivot": True},
        )
        prevent_reverting_properties(entity)
        d = entity.to_dict()

        self.assertNotIn("is_pivot", d)
        self.assertNotIn("IsPivot", d)

        add_props = d.get("additional_properties")
        self.assertNotIn("IsPivot", add_props)

    def test_prevent_reverting_properties_pivot_false(self):
        # If is_pivot is False, it returns early and nothing is stripped
        entity = MockEntity(
            is_pivot=False,
            additional_properties={"IsPivot": False},
        )
        prevent_reverting_properties(entity)
        d = entity.to_dict()

        self.assertTrue("is_pivot" in d)
        self.assertTrue("IsPivot" in d)

        add_props = d.get("additional_properties")
        self.assertIn("IsPivot", add_props)

    def test_prevent_reverting_properties_pivot_string_true(self):
        # If is_pivot is a string "true" in additional_properties, it is treated as True and stripped
        entity = MockEntity(
            is_pivot=False,
            additional_properties={"IsPivot": "true"},
        )
        prevent_reverting_properties(entity)
        d = entity.to_dict()

        self.assertNotIn("is_pivot", d)
        self.assertNotIn("IsPivot", d)
        add_props = d.get("additional_properties")
        self.assertNotIn("IsPivot", add_props)


if __name__ == "__main__":
    unittest.main()
