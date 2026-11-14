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

from typing import TYPE_CHECKING, Any

from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon.extraction import extract_configuration_param

from .constants import DEFAULT_API_ROOT, ENRICHMENT_PREFIX, INTEGRATION_NAME, RECENT_HISTORY_LIMIT
from .ransomleak_manager import RansomLeakManager, is_email

if TYPE_CHECKING:
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


def split_csv(value: str | None) -> list[str]:
    """Split a comma-separated parameter into unique, trimmed, non-empty values.

    Args:
        value: The raw parameter value.

    Returns:
        The values, in their original order.

    """
    values: list[str] = []
    seen: set[str] = set()
    for raw in (value or "").split(","):
        item = raw.strip()
        if item and item.lower() not in seen:
            seen.add(item.lower())
            values.append(item)
    return values


def user_entities(siemplify: SiemplifyAction) -> list[Any]:
    """Return the USER entities in scope of the action.

    Args:
        siemplify: The running action.

    Returns:
        The USER entities.

    """
    return [e for e in siemplify.target_entities if e.entity_type == EntityTypes.USER]


def collect_emails(siemplify: SiemplifyAction, csv_value: str | None) -> tuple[list[str], list[str]]:
    """Collect email addresses from USER entities plus a comma-separated parameter.

    Args:
        siemplify: The running action.
        csv_value: The raw comma-separated email parameter.

    Returns:
        (emails, skipped): lower-cased email addresses, and values that are not email addresses.

    """
    candidates = [e.identifier for e in user_entities(siemplify)] + split_csv(csv_value)
    emails: list[str] = []
    skipped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = candidate.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        if is_email(candidate):
            emails.append(key)
        else:
            skipped.append(candidate.strip())
    return emails, skipped


def training_summary(
    user: dict[str, Any],
    analytics: dict[str, Any],
    risk: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the per-user training summary used by enrichment and status actions.

    Args:
        user: The RansomLeak user record.
        analytics: The user's analytics record.
        risk: The user's Human Risk Score record, or None when unavailable.

    Returns:
        A flat-ish summary dict.

    """
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


def risk_summary(risk: dict[str, Any] | None) -> dict[str, Any]:
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


def user_summary(manager: RansomLeakManager, user: dict[str, Any]) -> dict[str, Any]:
    """Fetch analytics and risk for a user and build their summary.

    Args:
        manager: The RansomLeak client.
        user: The RansomLeak user record.

    Returns:
        Output of training_summary() including risk fields.

    """
    return training_summary(user, manager.get_user_analytics(user["id"]), manager.get_user_risk(user["id"]))


def enrichment_properties(summary: dict[str, Any]) -> dict[str, Any]:
    """Map a training summary to `RansomLeak_`-prefixed entity properties.

    Args:
        summary: Output of training_summary().

    Returns:
        Entity additional properties, without empty values.

    """
    keys = (
        "user_id",
        "team_name",
        "is_disabled",
        "exercises_completed",
        "learning_time_minutes",
        "campaigns_completed",
        "campaigns_in_progress",
        "campaigns_overdue",
        "average_quiz_score",
        "last_completed_at",
        "last_completed_exercise",
        "risk_score",
        "risk_level",
    )
    return {f"{ENRICHMENT_PREFIX}{key}": summary[key] for key in keys if summary.get(key) not in (None, "")}
