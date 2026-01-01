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

from typing import TYPE_CHECKING, NotRequired, Self, TypedDict

import mp.core.constants
import mp.core.utils
from mp.core.data_models.abc import RepresentableEnum, SequentialMetadata

if TYPE_CHECKING:
    from pathlib import Path


class TransformationFunction(RepresentableEnum):
    TO_STRING = 0
    TO_INTEGER = 1
    TO_DOUBLE = 2
    FROM_UNIX_TIME_STRING_OR_LONG = 3
    FROM_CUSTOM_DATE = 4
    TO_BOOLEAN = 5
    EXTRACT_REGEXP = 7
    EXTRACT_BY_REGEX_WITH_GROUP = 15
    TO_IS_CORRELATION = 100
    TO_IP_ADDRESS = 101
    TO_LIST_OF_LONGS_SEPERATED_COMMA = 102
    SUBSTR_BY_LENGTH = 103
    SUBSTR_BY_END_TEXT = 105
    FIRST_LINES = 106
    JOIN_RAW_FIELDS = 107
    STATIC_VALUE = 108
    EXTRACT_DOMAIN_FROM_URI = 109
    CLEAN_URL = 110


class ComparisonType(RepresentableEnum):
    EQUAL = 0
    CONTAINS = 1
    STARTS_WITH = 2
    ENDS_WITH = 3


class ExtractionFunction(RepresentableEnum):
    NONE = 0
    REGEX = 1
    DELIMITER = 2


class BuiltMappingRule(TypedDict):
    Source: str
    Product: str | None
    EventName: str | None
    SecurityEventFieldName: str
    TransformationFunction: int
    TransformationFunctionParam: str | None
    RawDataPrimaryFieldMatchTerm: str
    RawDataPrimaryFieldComparisonType: int
    RawDataSecondaryFieldMatchTerm: str | None
    RawDataSecondaryFieldComparisonType: int
    RawDataThirdFieldMatchTerm: str | None
    RawDataThirdFieldComparisonType: int
    IsArtifact: bool
    ExtractionFunctionParam: str | None
    ExtractionFunction: int


class NonBuiltMappingRule(TypedDict):
    source: str
    product: NotRequired[str | None]
    event_name: NotRequired[str | None]
    security_event_file_name: str
    transformation_function: str
    transformation_function_param: NotRequired[str | None]
    raw_data_primary_field_match_term: NotRequired[str]
    raw_data_primary_field_comparison_type: NotRequired[str]
    raw_data_secondary_field_match_term: NotRequired[str | None]
    raw_data_secondary_field_comparison_type: NotRequired[str]
    raw_data_third_field_match_term: NotRequired[str | None]
    raw_data_third_field_comparison_type: NotRequired[str]
    is_artifact: bool
    extract_function_param: NotRequired[str | None]
    extract_function: NotRequired[str]


class MappingRule(SequentialMetadata[BuiltMappingRule, NonBuiltMappingRule]):
    source: str
    product: str | None
    event_name: str | None
    security_event_file_name: str
    transformation_function: TransformationFunction
    transformation_function_param: str | None
    raw_data_primary_field_match_term: str
    raw_data_primary_field_comparison_type: ComparisonType
    raw_data_secondary_field_match_term: str | None
    raw_data_secondary_field_comparison_type: ComparisonType
    raw_data_third_field_match_term: str | None
    raw_data_third_field_comparison_type: ComparisonType
    is_artifact: bool
    extract_function_param: str | None
    extract_function: ExtractionFunction

    @classmethod
    def from_built_path(cls, path: Path) -> list[Self]:
        """Create based on the metadata files found in the built-integration path.

        Args:
            path: the path to the built integration

        Returns:
            A sequence of `MappingRule` objects

        """
        meta_path: Path = (
            path
            / mp.core.constants.OUT_MAPPING_RULES_DIR
            / mp.core.constants.OUT_MAPPING_RULES_FILE
        )
        if not meta_path.exists():
            return []

        return cls._from_built_path(meta_path)

    @classmethod
    def from_non_built_path(cls, path: Path) -> list[Self]:
        """Create based on the metadata files found in the non-built-integration path.

        Args:
            path: the path to the non-built integration

        Returns:
            A sequence of `MappingRule` objects

        """
        meta_path: Path = path / mp.core.constants.MAPPING_RULES_FILE
        if not meta_path.exists():
            return []

        return cls._from_non_built_path(meta_path)

    @classmethod
    def _from_built(cls, built: BuiltMappingRule) -> Self:
        extract_function: int | None = built.get("ExtractionFunction")
        if extract_function is None:
            extract_function = ExtractionFunction.NONE.value

        return cls(
            source=built["Source"] or "",
            product=built["Product"],
            event_name=built["EventName"],
            security_event_file_name=built["SecurityEventFieldName"],
            transformation_function=TransformationFunction(
                built["TransformationFunction"],
            ),
            transformation_function_param=built["TransformationFunctionParam"],
            raw_data_primary_field_match_term=(built.get("RawDataPrimaryFieldMatchTerm") or ""),
            raw_data_primary_field_comparison_type=ComparisonType(
                built["RawDataPrimaryFieldComparisonType"],
            ),
            raw_data_secondary_field_match_term=built["RawDataSecondaryFieldMatchTerm"],
            raw_data_secondary_field_comparison_type=ComparisonType(
                built["RawDataSecondaryFieldComparisonType"],
            ),
            raw_data_third_field_match_term=built["RawDataThirdFieldMatchTerm"],
            raw_data_third_field_comparison_type=ComparisonType(
                built["RawDataThirdFieldComparisonType"],
            ),
            is_artifact=built["IsArtifact"],
            extract_function_param=built.get("ExtractionFunctionParam"),
            extract_function=ExtractionFunction(extract_function),
        )

    @classmethod
    def _from_non_built(cls, non_built: NonBuiltMappingRule) -> Self:
        extract_function: str | None = non_built.get("extract_function")
        if extract_function is None:
            extract_function = ExtractionFunction.NONE.to_string()

        return cls(
            source=non_built["source"],
            product=non_built.get("product"),
            event_name=non_built.get("event_name"),
            security_event_file_name=non_built["security_event_file_name"],
            transformation_function=TransformationFunction.from_string(
                non_built.get(
                    "transformation_function",
                    TransformationFunction.TO_STRING.to_string(),
                ),
            ),
            raw_data_primary_field_match_term=(
                non_built.get("raw_data_primary_field_match_term", "")
            ),
            raw_data_primary_field_comparison_type=ComparisonType.from_string(
                non_built.get(
                    "raw_data_primary_field_comparison_type",
                    ComparisonType.EQUAL.to_string(),
                ),
            ),
            raw_data_secondary_field_match_term=(
                non_built.get("raw_data_secondary_field_match_term", "")
            ),
            raw_data_secondary_field_comparison_type=ComparisonType.from_string(
                non_built.get(
                    "raw_data_secondary_field_comparison_type",
                    ComparisonType.EQUAL.to_string(),
                ),
            ),
            raw_data_third_field_match_term=(non_built.get("raw_data_third_field_match_term", "")),
            raw_data_third_field_comparison_type=ComparisonType.from_string(
                non_built.get(
                    "raw_data_third_field_comparison_type",
                    ComparisonType.EQUAL.to_string(),
                ),
            ),
            is_artifact=non_built["is_artifact"],
            extract_function_param=non_built.get("extract_function_param"),
            extract_function=ExtractionFunction.from_string(extract_function),
            transformation_function_param=non_built.get(
                "transformation_function_param",
            ),
        )

    def to_built(self) -> BuiltMappingRule:
        """Create a built mapping rule metadata dict.

        Returns:
            A built version of the mapping rule metadata dict

        """
        return BuiltMappingRule(
            Source=self.source,
            Product=self.product,
            EventName=self.event_name,
            SecurityEventFieldName=self.security_event_file_name,
            TransformationFunction=self.transformation_function.value,
            TransformationFunctionParam=self.transformation_function_param,
            RawDataPrimaryFieldMatchTerm=self.raw_data_primary_field_match_term,
            RawDataPrimaryFieldComparisonType=self.raw_data_primary_field_comparison_type.value,
            RawDataSecondaryFieldMatchTerm=self.raw_data_secondary_field_match_term,
            RawDataSecondaryFieldComparisonType=(
                self.raw_data_secondary_field_comparison_type.value
            ),
            RawDataThirdFieldMatchTerm=self.raw_data_third_field_match_term,
            RawDataThirdFieldComparisonType=(self.raw_data_third_field_comparison_type.value),
            IsArtifact=self.is_artifact,
            ExtractionFunctionParam=self.extract_function_param,
            ExtractionFunction=self.extract_function.value,
        )

    def to_non_built(self) -> NonBuiltMappingRule:
        """Create a non-built mapping rule metadata dict.

        Returns:
            A non-built version of the mapping rule metadata dict

        """
        non_built: NonBuiltMappingRule = NonBuiltMappingRule(
            source=self.source,
            product=self.product,
            event_name=self.event_name,
            security_event_file_name=self.security_event_file_name,
            transformation_function=self.transformation_function.to_string(),
            transformation_function_param=self.transformation_function_param,
            raw_data_primary_field_match_term=self.raw_data_primary_field_match_term,
            raw_data_primary_field_comparison_type=(
                self.raw_data_primary_field_comparison_type.to_string()
            ),
            raw_data_secondary_field_match_term=(self.raw_data_secondary_field_match_term),
            raw_data_secondary_field_comparison_type=(
                self.raw_data_secondary_field_comparison_type.to_string()
            ),
            raw_data_third_field_match_term=self.raw_data_third_field_match_term,
            raw_data_third_field_comparison_type=(
                self.raw_data_third_field_comparison_type.to_string()
            ),
            is_artifact=self.is_artifact,
            extract_function_param=self.extract_function_param,
            extract_function=self.extract_function.to_string(),
        )
        mp.core.utils.remove_none_entries_from_mapping(non_built)
        return non_built
