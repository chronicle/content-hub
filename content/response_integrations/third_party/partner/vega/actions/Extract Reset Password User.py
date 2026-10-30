from __future__ import annotations

from typing import Any

from TIPCommon.base.action import Action

from ..core.case_events import case_events
from ..core.constants import EXTRACT_RESET_PASSWORD_USER_SCRIPT_NAME
from ..core.mapping import reset_password_users_from_payload


def _event_payload(event: Any) -> dict[str, Any]:
    if isinstance(event, dict):
        payload = dict(event)
    else:
        payload = {}
        extra = getattr(event, "additional_properties", None)
        if isinstance(extra, dict):
            payload.update(extra)
        for key in (
            "recommended_actions",
            "recommendedActions",
            "vega_reset_password_user",
            "details",
            "user",
        ):
            value = getattr(event, key, None)
            if value not in (None, ""):
                payload.setdefault(key, value)
    extra = payload.get("additional_properties") or payload.get("additionalProperties")
    if isinstance(extra, dict):
        merged = dict(extra)
        merged.update(payload)
        return merged
    return payload


class ExtractResetPasswordUser(Action):
    """Read Okta reset target emails from case recommendedActions."""

    def __init__(self) -> None:
        super().__init__(EXTRACT_RESET_PASSWORD_USER_SCRIPT_NAME)

    def _init_api_clients(self) -> None:
        """No remote API client."""

    def _perform_action(self, _=None) -> None:
        users: list[str] = []
        for event in case_events(self.soar_action):
            for user in reset_password_users_from_payload(_event_payload(event)):
                if user not in users:
                    users.append(user)
        self.json_results = {"user_id": ",".join(users), "users": users}
        if not users:
            self.result_value = False
            self.output_message = "No reset_user_password target email was found on this case."
            return
        self.output_message = f"Found Okta reset target(s): {', '.join(users)}."


def main() -> None:
    ExtractResetPasswordUser().run()


if __name__ == "__main__":
    main()
