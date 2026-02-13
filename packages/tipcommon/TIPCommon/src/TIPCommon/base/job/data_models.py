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

import hashlib
from typing import NamedTuple
from dataclasses import dataclass, field
from ...data_models import AlertCard, CaseDataStatus, CaseDetails, JobParamType
from ...types import SingleJson
from ...consts import JOB_MAX_TAG_LEN, JOB_MIN_TAG_LEN


class JobParameter:
    """A general script parameter object.
    Attributes:
        full_dict (dict[str, any]): The original dict received from the API.
        id (int | None): The parameter's ID.
        is_mandatory (bool):
            Whether the parameter is mandatory or not.
            (prioritized over 'value' in playbooks).
        name (str | None): The parameter's name.
        type (ActionParamType): The type of the parameter.
        value (any):
            The default value of the parameter
            (prioritized over 'default_value' in manual actions).
    """

    def __init__(self, input_dict: SingleJson) -> None:
        self.full_dict: SingleJson = input_dict
        self.id_: int | None = input_dict.get("id")
        self.is_mandatory: bool = input_dict.get(
            "mandatory",
            input_dict.get("isMandatory", False),
        )
        self.name: str = input_dict.get(
            "displayName",
            input_dict.get("name", "No name found!"),
        )
        self.type_ = self._parse_job_param_type(input_dict.get("type", -1))
        self.value: any = input_dict.get("value")

    def _parse_job_param_type(self, type_value: str | int) -> JobParamType:
        """Parses and returns the JobParamType from a string or integer value."""
        if isinstance(type_value, str):
            normalized = type_value.strip().upper()
            if normalized in ("INT"):
                return JobParamType.INTEGER
            if normalized in JobParamType.__members__:
                return JobParamType[normalized]
            return JobParamType.NULL

        if isinstance(type_value, int):
            try:
                return JobParamType(type_value)
            except ValueError:
                return JobParamType.NULL
        return JobParamType.NULL


class JobCommentsResult(NamedTuple):
    product_comments_sync_to_case: list[str]
    case_comments_sync_to_product: list[str]


class JobTagsResult(NamedTuple):
    product_tags_sync_to_case: ProductTagsData
    case_tags_sync_to_product: CaseTagsData


class BaseTagsData(NamedTuple):
    tags_to_add: list[str]
    tags_to_remove: list[str]


class ProductTagsData(BaseTagsData): ...


class CaseTagsData(BaseTagsData): ...


@dataclass
class SyncMetadata:
    status: str = None
    severity: str = None
    assignee: str = None
    closure_comment: str = None
    incident_id: str = None
    incident_number: str = None
    closure_reason: str = None
    determination: str = None


class JobStatusResult(NamedTuple):
    alerts_to_close_in_soar: list[tuple[AlertCard, SyncMetadata]]
    incidents_to_close_in_product: list[dict[str, any]]


class JobAssigneeResult(NamedTuple):
    target_user: dict[str, any] | None
    alert: AlertCard | None


class JobSeverityResult(NamedTuple):
    updates: list[tuple[AlertCard, str]]


@dataclass(slots=True)
class JobCase:
    case_detail: CaseDetails
    modification_time: int
    alert_metadata: dict[str, SyncMetadata] = field(default_factory=dict)
    product_ids_from_secops_alerts: dict[str, AlertCard] = field(default_factory=dict)

    def get_first_alert(self, open_only: bool = True) -> AlertCard | None:
        """Fetches the first alert in the case."""
        if open_only:
            return next(
                (alert for alert in self.case_detail.alerts if alert.status.lower() == "open"),
                None,
            )
        return self.case_detail.alerts[0]

    def get_alert_identifier_from_product_id(
        self,
        product_id: str,
    ) -> str | None:
        """Fetches alert identifier from product ID."""
        alert = self.product_ids_from_secops_alerts.get(product_id)
        if alert:
            return alert.identifier
        return None

    @property
    def case_comments(self) -> list[str]:
        return self.case_detail.comments

    @case_comments.setter
    def case_comments(self, value: list[str]) -> None:
        self.case_detail.comments = value

    def add_product_incident(
        self,
        incident,
        product_key="name",
    ) -> None:
        """Adds a product incident to the corresponding alert in the case."""
        incident_product_id = getattr(incident, product_key)
        alert = self.product_ids_from_secops_alerts.get(incident_product_id)
        if alert:
            alert.incident = incident

    def get_product_incident(
        self,
        alert_id: str,
    ) -> SingleJson | None:
        """Fetches the product incident for the given alert ID."""
        for product_id, alert in self.product_ids_from_secops_alerts.items():
            if product_id == alert_id and hasattr(alert, "incident"):
                return alert.incident
        return None

    def add_product_comment(
        self,
        incident_id: str,
        comment: str,
        product_key: str = "id",
    ) -> None:
        """Adds a product comment to the corresponding incident in the case."""
        product_comments = [comment]
        matched_incident = next(
            (
                alert.incident
                for alert in self.case_detail.alerts
                if getattr(alert.incident, product_key) == incident_id
            ),
            None,
        )
        if matched_incident:
            if not matched_incident.comments:
                matched_incident.comments = product_comments
            else:
                matched_incident.comments.extend(product_comments)

    def get_comments_to_sync(
        self,
        product_comment_prefix: str,
        case_comment_prefix: str,
        product_comment_key: str = "message",
        product_incident_key: str = "name",
    ) -> JobCommentsResult:
        """Get comments to sync between product and case."""
        case_hashes = self.get_case_comments_hashes()
        product_hashes = self.get_product_comments_hashes()

        return JobCommentsResult(
            product_comments_sync_to_case=self._collect_product_comments_to_case(
                product_comment_prefix,
                case_comment_prefix,
                product_comment_key,
                product_incident_key,
                case_hashes,
            ),
            case_comments_sync_to_product=self._collect_case_comments_to_product(
                case_comment_prefix,
                product_comment_prefix,
                product_hashes,
            ),
        )

    def _collect_product_comments_to_case(
        self,
        product_prefix: str,
        case_prefix: str,
        comment_key: str,
        incident_key: str,
        case_hashes: list[str],
    ) -> list[str]:
        results: list[str] = []

        for alert in self.case_detail.alerts:
            incident = getattr(alert, "incident", None)
            if not incident:
                continue

            alert_id = alert.alert_group_identifier
            incident_id = getattr(incident, incident_key)

            for product_comment in incident.comments:
                text = getattr(product_comment, comment_key, "")
                if not self._is_valid_product_comment(text, case_prefix):
                    continue

                formatted = f"{product_prefix}{incident_id}: {text}"
                if self._generate_string_hash(formatted) in case_hashes:
                    continue

                results.append(f"{alert_id}:{formatted}")

        return results

    def _collect_case_comments_to_product(
        self,
        case_prefix: str,
        product_prefix: str,
        product_hashes: list[str],
    ) -> list[str]:
        results: list[str] = []

        for comment in self.case_comments:
            text = comment.get("comment", "")
            if not self._is_valid_secops_comment(comment, product_prefix):
                continue

            formatted = f"{case_prefix}{self.case_detail.id_}: {text}"
            if self._generate_string_hash(formatted) in product_hashes:
                continue

            results.append(formatted)

        return results

    def _is_valid_secops_comment(
        self,
        comment: SingleJson,
        product_comment_prefix: str
    ) -> bool:
        """
        Checks if a Google SecOps comment should be synced to product.
        """
        content: str = comment.get("comment", "") or ""
        return bool(content.strip()) and not content.startswith(product_comment_prefix)

    def _is_valid_product_comment(self, comment: str, case_comment_prefix: str) -> bool:
        """ "
        Checks if a product comment is valid or not.
        """
        content: str = comment
        return bool(content) and not content.startswith(case_comment_prefix)

    def get_case_comments_hashes(self) -> list[str]:
        """Get hashes of all case comments."""
        return [
            self._generate_string_hash(
                comment["comment"] or ""
            ) for comment in self.case_comments
        ]

    def get_product_comments_hashes(self) -> list[str]:
        """Get hashes of all product comments in the case alerts."""
        comments_hashes = []
        for alert in self.case_detail.alerts:
            if not hasattr(alert, "incident") or alert.incident is None:
                continue
            for comment in alert.incident.comments:
                comments_hashes.append(
                    self._generate_string_hash(comment.message or "")
                )
        return comments_hashes

    def _generate_string_hash(self, text: str) -> str:
        """Generates a SHA256 hash for a given string."""
        return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

    def get_product_tags_to_sync_to_products(
        self,
        product_properties_key: str | None = None,
        tags_key="tags",
        tags_name="name"
    ) -> tuple[list[SingleJson], list[str]]:
        """Get product map dict with the comments to be synced to all product ids."""
        all_tags = self.__get_all_product_tags(
            product_properties_key=product_properties_key, tags_key=tags_key
        )
        incident_to_update_tags = []
        for alert in self.case_detail.alerts:
            if not hasattr(alert, "incident") or alert.incident is None:
                continue
            incident = alert.incident
            tags = set(getattr(incident, tags_key, []))
            tags = [
                getattr(tag, tags_name, None) if getattr(tag, tags_name, None) else tag
                for tag in tags
            ]
            tags_to_update = set(all_tags).difference(tags)
            if tags_to_update:
                incident_to_update_tags.append(incident)
        return incident_to_update_tags, all_tags

    def __get_all_product_tags(
        self,
        product_properties_key: str | None = None,
        tags_key="tags",
        tags_name="name"
    ) -> list[str]:
        """Get all product tags from the case alerts."""
        all_tags = set()
        for alert in self.case_detail.alerts:
            if not hasattr(alert, "incident") or alert.incident is None:
                continue
            incident = alert.incident
            incident = (
                getattr(incident, product_properties_key, {})
                if product_properties_key
                else incident
            )
            tags = getattr(incident, tags_key, [])
            tags = [
                getattr(tag, tags_name, None) if getattr(tag, tags_name, None) else tag
                for tag in tags
            ]
            all_tags.update(tags)
        return list(all_tags)

    def __get_all_case_tags(self) -> list[str]:
        """Get all case tags."""
        return [
            tag[
                "displayName"
            ] if "displayName" in tag else tag for tag in self.case_detail.tags
        ]

    def product_tags(
        self,
        product_properties_key: str | None = None,
        tags_key="tags",
        tags_name="name"
    ) -> list[str]:
        """Get all product tags from the case alerts."""
        return self.__get_all_product_tags(
            product_properties_key=product_properties_key,
            tags_key=tags_key,
            tags_name=tags_name,
        )

    @property
    def case_tags(self) -> list[str]:
        """Get all case tags."""
        return self.__get_all_case_tags()

    def get_tags_to_sync(
        self,
        product_tag_prefix: str,
        case_tag_prefix: str,
        tag_to_exclude: str,
        product_properties_key: str | None = None,
        product_tags_key: str = "tags",
        product_tags_name: str = "name",
    ) -> JobTagsResult:
        case_tags = self.case_tags
        product_tags = self.product_tags(
            product_properties_key,
            product_tags_key,
            product_tags_name,
        )

        return JobTagsResult(
            product_tags_sync_to_case=self._build_product_to_case_tags(
                case_tags, product_tags, product_tag_prefix, case_tag_prefix
            ),
            case_tags_sync_to_product=self._build_case_to_product_tags(
                case_tags,
                product_tags,
                case_tag_prefix,
                product_tag_prefix,
                tag_to_exclude,
            ),
        )

    def _build_case_to_product_tags(
        self,
        case_tags: list[str],
        product_tags: list[str],
        case_prefix: str,
        product_prefix: str,
        tag_to_exclude: str,
    ) -> CaseTagsData:
        return CaseTagsData(
            tags_to_add=self._get_new_tags(
                case_tags,
                product_tags,
                case_prefix,
                product_prefix,
                tag_to_exclude,
            ),
            tags_to_remove=self._get_tags_to_remove(
                case_tags,
                product_tags,
                case_prefix,
            ),
        )

    def _build_product_to_case_tags(
        self,
        case_tags: list[str],
        product_tags: list[str],
        product_prefix: str,
        case_prefix: str,
    ) -> ProductTagsData:
        return ProductTagsData(
            tags_to_add=self._get_new_tags(
                product_tags,
                case_tags,
                product_prefix,
                case_prefix,
            ),
            tags_to_remove=self._get_tags_to_remove(
                product_tags,
                case_tags,
                product_prefix,
            ),
        )

    def _get_new_tags(
        self,
        source_tags: list[str],
        existing_tags: list[str],
        prefix_to_add: str,
        prefix_to_exclude: str,
        tag_to_exclude: str | None = None,
        min_len: int = JOB_MIN_TAG_LEN,
        max_len: int = JOB_MAX_TAG_LEN,
    ) -> list[str]:
        """
        Identifies tags from source_tags that should be added to the destination system.
        """
        new_tags = []
        for tag in source_tags:
            stripped_tag = tag.strip()
            if self._is_tag_valid(
                stripped_tag, prefix_to_exclude, tag_to_exclude, min_len, int(max_len)
            ):
                prefixed_tag = f"{prefix_to_add}{stripped_tag}"
                if prefixed_tag not in existing_tags:
                    new_tags.append(prefixed_tag)
        return new_tags

    def _get_tags_to_remove(
        self,
        source_tags: list[str],
        destination_tags: list[str],
        source_prefix: str,
    ) -> list[str]:
        """
        Identifies tags to be removed from the destination system based on 
        source prefix.
        """
        source_tags_prefixed = {f"{source_prefix}{tag.strip()}" for tag in source_tags}
        return [
            dest_tag
            for dest_tag in destination_tags
            if dest_tag.startswith(
                source_prefix
            ) and dest_tag not in source_tags_prefixed
        ]

    def _is_tag_valid(
        self,
        stripped_tag: str,
        prefix_to_exclude: str,
        tag_to_exclude: str | None,
        min_len: int,
        max_len: int,
    ) -> bool:
        """
        Checks if a stripped tag meets all exclusion and length criteria.
        """
        if not stripped_tag:
            return False
        if tag_to_exclude and stripped_tag == tag_to_exclude:
            return False
        if stripped_tag.startswith(prefix_to_exclude):
            return False
        return min_len <= len(stripped_tag) <= max_len

    def get_assignee_to_sync(self, secops_users: list[dict]) -> JobAssigneeResult:
        """Finds the first open alert and matches the source assignee."""
        first_open_alert = self.get_first_alert(open_only=True)
        if not first_open_alert:
            return JobAssigneeResult(None, None)
        meta = self.alert_metadata.get(first_open_alert.identifier)
        if not meta or not meta.assignee:
            return JobAssigneeResult(None, None)
        if "@" in meta.assignee:
            target_user = next(
                (user for user in secops_users if user.get("email") == meta.assignee),
                None,
            )
        else:
            target_user = next(
                (user for user in secops_users if user.get(
                    "userFullName") == meta.assignee
                ),
                None,
            )
        return JobAssigneeResult(target_user, first_open_alert)

    def get_severity_to_sync(self, severity_map: dict) -> JobSeverityResult:
        """Fetches severity updates for alerts based on metadata and severity map."""
        updates = []
        for alert in self.case_detail.alerts:
            meta = self.alert_metadata.get(alert.identifier)
            if meta and meta.severity:
                mapped_sev = severity_map.get(meta.severity)
                if mapped_sev and mapped_sev.lower() != alert.priority.lower():
                    updates.append((alert, mapped_sev))
        return JobSeverityResult(updates)

    def get_status_to_sync(self, product_closed_status: str) -> JobStatusResult:
        product_to_secops = []
        secops_to_product = []
        is_case_closed = self._is_case_closed()

        for alert in self.case_detail.alerts:
            meta = self.alert_metadata.get(alert.identifier)
            if not meta:
                continue

            if self._should_close_alert_in_secops(alert, meta, product_closed_status):
                product_to_secops.append((alert, meta))
            elif self._should_close_alert_in_product(
                alert, meta, is_case_closed, product_closed_status
            ):
                secops_to_product.append(
                    self._build_product_closure_payload(alert, meta, is_case_closed)
                )

        return JobStatusResult(product_to_secops, secops_to_product)

    def _is_case_closed(self) -> bool:
        return self.case_detail.status == CaseDataStatus.CLOSED

    def _should_close_alert_in_secops(
        self,
        alert: AlertCard,
        meta: SyncMetadata,
        closed_status: str
    ) -> bool:
        return meta.status == closed_status and alert.status.lower() != "close"

    def _should_close_alert_in_product(
        self,
        alert: AlertCard,
        meta: SyncMetadata,
        is_case_closed: bool,
        closed_status: str
    ) -> bool:
        if meta.status == closed_status:
            return False
        return is_case_closed or (
            alert.status.lower() == "close" and len(self.case_detail.alerts) > 1
        )

    def _build_product_closure_payload(
        self,
        alert: AlertCard,
        meta: SyncMetadata,
        is_case_closed: bool
    ) -> SingleJson:
        payload = {
            "alert": alert,
            "is_case_closed": is_case_closed,
            "meta": meta,
        }
        if not is_case_closed:
            payload.update(alert.closure_details)
        return payload
