# Copyright 2026 RansomLeak
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

"""Helpers shared by the RansomLeak actions."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.transformation import string_to_multi_value
from TIPCommon.types import SingleJson

from .constants import (
    DEFAULT_API_ROOT,
    ENRICHMENT_PREFIX,
    INTEGRATION_NAME,
    MAX_LOOKUP_WORKERS,
    RECENT_HISTORY_LIMIT,
    SUMMARY_FIELDS,
)
from .ransomleak_manager import RansomLeakManager, is_email

if TYPE_CHECKING:
    from collections.abc import Callable

    from soar_sdk.SiemplifyAction import SiemplifyAction


def build_manager(siemplify: SiemplifyAction) -> RansomLeakManager:
    """Create a manager from the integration configuration.

    Args:
        siemplify: The running action.

    Returns:
        A configured RansomLeakManager.

    """
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        default_value=DEFAULT_API_ROOT,
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        print_value=True,
    )
    return RansomLeakManager(api_root=api_root, api_key=api_key, verify_ssl=verify_ssl)


def user_entities(siemplify: SiemplifyAction) -> list[Any]:
    """Return the USER entities in scope of the action.

    Args:
        siemplify: The running action.

    Returns:
        The USER entities.

    """
    return [e for e in siemplify.target_entities if e.entity_type == EntityTypes.USER]


def unique_values(csv_value: str | None) -> list[str]:
    """Split a comma-separated parameter, deduped case-insensitively (first-seen spelling kept).

    Args:
        csv_value: The raw comma-separated parameter.

    Returns:
        The distinct values, in input order.

    """
    return _dedupe_casefold(string_to_multi_value(csv_value, only_unique=True))


def _dedupe_casefold(values: list[str]) -> list[str]:
    seen: dict[str, str] = {}
    for value in values:
        seen.setdefault(value.lower(), value)
    return list(seen.values())


def collect_emails(siemplify: SiemplifyAction, csv_value: str | None) -> tuple[list[str], list[str]]:
    """Collect email addresses from USER entities plus a comma-separated parameter.

    Args:
        siemplify: The running action.
        csv_value: The raw comma-separated email parameter.

    Returns:
        (emails, skipped): lower-cased email addresses, and values that are not email addresses.

    """
    candidates = [e.identifier.strip() for e in user_entities(siemplify)]
    candidates += string_to_multi_value(csv_value, only_unique=True)
    # Deduped once here (first-seen order), case-insensitively; emails are lower-cased.
    emails = list(dict.fromkeys(c.lower() for c in candidates if is_email(c)))
    skipped = _dedupe_casefold([c for c in candidates if not is_email(c)])
    return emails, skipped


def section(title: str, values: list[str]) -> str:
    """Format an output-message section listing values, or "" when there are none.

    Args:
        title: The section heading.
        values: The values to list.

    Returns:
        A newline-prefixed section, or an empty string.

    """
    return f"\n{title}:\n" + "\n".join(values) if values else ""


def training_summary(
    user: SingleJson,
    analytics: SingleJson,
    risk: SingleJson | None = None,
) -> SingleJson:
    """Build the per-user training summary used by enrichment and status actions.

    Args:
        user: The RansomLeak user record.
        analytics: The user's analytics record.
        risk: The user's Human Risk Score record, or None when unavailable.

    Returns:
        A flat-ish summary dict.

    """
    analytics = analytics or {}
    history = sorted(
        analytics.get("exerciseHistory") or [],
        key=lambda h: h.get("completedAt") or "",
        reverse=True,
    )
    return {
        "user_id": user.get("id"),
        "email": user.get("email"),
        "first_name": user.get("firstName"),
        "last_name": user.get("lastName"),
        "external_id": user.get("externalId"),
        "team_name": user.get("teamName"),
        "is_disabled": user.get("isDisabled"),
        "created_at": user.get("createdAt"),
        "exercises_completed": analytics.get("exercisesCompleted"),
        "learning_time_minutes": analytics.get("totalLearningTimeMinutes"),
        "campaigns_completed": analytics.get("campaignsCompleted"),
        "campaigns_in_progress": analytics.get("campaignsInProgress"),
        "campaigns_overdue": analytics.get("campaignsOverdue"),
        "average_quiz_score": analytics.get("averageQuizScore"),
        "last_completed_at": history[0].get("completedAt") if history else None,
        "last_completed_exercise": history[0].get("exerciseName") if history else None,
        "recent_completions": history[:RECENT_HISTORY_LIMIT],
        **risk_summary(risk),
    }


def risk_summary(risk: SingleJson | None) -> SingleJson:
    """Flatten a Human Risk Score record. Every value is None when no score is available.

    Args:
        risk: The `/users/{id}/risk` response, or None (older RansomLeak, not computed).

    Returns:
        `risk_score`, `risk_level`, `risk_confidence`, `risk_computed_at` and `risk_sub_scores`.

    """
    risk = risk or {}
    return {
        "risk_score": risk.get("score"),
        "risk_level": risk.get("level"),
        "risk_confidence": risk.get("confidence"),
        "risk_computed_at": risk.get("computedAt"),
        "risk_sub_scores": risk.get("subScores"),
    }


def user_summary(manager: RansomLeakManager, user: SingleJson) -> SingleJson:
    """Fetch analytics and risk for a user and build their summary.

    Args:
        manager: The RansomLeak client.
        user: The RansomLeak user record.

    Returns:
        Output of training_summary() including risk fields.

    """
    return training_summary(user, manager.get_user_analytics(user["id"]), manager.get_user_risk(user["id"]))


def enrichment_properties(summary: SingleJson) -> SingleJson:
    """Map a training summary to `RansomLeak_`-prefixed entity properties.

    Args:
        summary: Output of training_summary().

    Returns:
        Entity additional properties, without empty values.

    """
    keys = ("user_id", "team_name", "is_disabled", *(key for key, _ in SUMMARY_FIELDS))
    return {f"{ENRICHMENT_PREFIX}{key}": summary[key] for key in keys if summary.get(key) not in (None, "")}


def map_concurrently(fn: Callable[[str], Any], items: list[str]) -> list[tuple[str, Any, Exception | None]]:
    """Run fn over items with a small thread pool, keeping input order.

    Args:
        fn: Called once per item.
        items: The inputs.

    Returns:
        (item, result, error) per item, in input order; error is set (and result None) when fn raised.

    """

    def run(item: str) -> tuple[str, Any, Exception | None]:
        try:
            return item, fn(item), None
        except Exception as error:  # noqa: BLE001 - reported per item by the caller
            return item, None, error

    if not items:
        return []
    with ThreadPoolExecutor(max_workers=min(MAX_LOOKUP_WORKERS, len(items))) as pool:
        return list(pool.map(run, items))


def lookup_user_summary(manager: RansomLeakManager, email: str) -> SingleJson | None:
    """Find a user by email and build their summary.

    Args:
        manager: The RansomLeak client.
        email: The user's email address.

    Returns:
        Output of user_summary(), or None when no user matches.

    """
    user = manager.get_user_by_email(email)
    return None if user is None else user_summary(manager, user)
