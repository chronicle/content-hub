"""
SpyCloud Enterprise - Filter Passwords By Policy

Decides whether a case's exposed passwords still matter under the organization's
password policy, so the Entra ID response playbook can gate a password reset.

The action reads the plaintext password values the connector flattened onto the
case's security events (present only when the connector's "Include Plaintext
Secrets" option was enabled at collection time) and drops any password that does
not satisfy the configured policy:

  - Minimum Password Length: passwords shorter than this are dropped.
  - Require Symbol: when enabled, passwords with no punctuation symbol are dropped.

A password that still matches the policy is one Entra ID would accept, so an
exposed copy of it is a live account-takeover risk worth resetting. ``result_value``
is the number of policy-conforming exposed passwords that remain after filtering;
the playbook resets the user's password only when it is greater than zero.

Data source: this action does NOT call the SpyCloud API. It reads the exposures
already attached to the case, exactly like Get Watchlist Exposures.

Sensitive data: plaintext passwords are never surfaced. The JSON result reports
only counts, the configured policy, and length-only masked placeholders, alongside
the case ID and a UTC timestamp for audit.
"""
from __future__ import annotations

from datetime import datetime, timezone

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core import datamodels
from ..core.Constants import FILTER_PASSWORDS_BY_POLICY_SCRIPT_NAME

SCRIPT_NAME = FILTER_PASSWORDS_BY_POLICY_SCRIPT_NAME

MIN_LENGTH_PARAM = "Minimum Password Length"
REQUIRE_SYMBOL_PARAM = "Require Symbol"
DEFAULT_MIN_LENGTH = 8
DEFAULT_REQUIRE_SYMBOL = True


@output_handler
def main() -> None:
    """Filter the case's exposed passwords against the configured password policy."""
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = 0
    output_message = ""

    try:
        minimum_length = siemplify.extract_action_param(
            param_name=MIN_LENGTH_PARAM,
            is_mandatory=False,
            input_type=int,
            default_value=DEFAULT_MIN_LENGTH,
            print_value=True,
        )
        require_symbol = siemplify.extract_action_param(
            param_name=REQUIRE_SYMBOL_PARAM,
            is_mandatory=False,
            input_type=bool,
            default_value=DEFAULT_REQUIRE_SYMBOL,
            print_value=True,
        )

        siemplify.LOGGER.info(
            f"Password policy: minimum length {minimum_length}, "
            f"require symbol {require_symbol}"
        )

        # Group the policy decision per exposed identity so an analyst can see
        # which user's exposure drove the reset. Values are masked; only lengths
        # and pass/fail are recorded.
        per_email: dict[str, dict] = {}
        total_passwords = 0
        remaining = 0

        alerts = siemplify.case.alerts or []
        siemplify.LOGGER.info(f"Scanning {len(alerts)} alert(s) in the case")

        for alert in alerts:
            for event in getattr(alert, "security_events", []) or []:
                props = getattr(event, "additional_properties", {}) or {}
                if not datamodels.is_spycloud_event(props):
                    continue
                passwords = datamodels.collect_plaintext_passwords(props)
                if not passwords:
                    continue
                email = str(props.get("spycloud_email", "") or "").strip().lower()
                bucket = per_email.setdefault(
                    email, {"email": email, "kept": [], "dropped": []}
                )
                for password in passwords:
                    total_passwords += 1
                    matches = datamodels.password_matches_policy(
                        password, minimum_length, require_symbol
                    )
                    entry = {
                        "masked": datamodels.mask_password(password),
                        "length": len(password),
                        "has_symbol": datamodels.has_symbol(password),
                    }
                    if matches:
                        remaining += 1
                        bucket["kept"].append(entry)
                    else:
                        bucket["dropped"].append(entry)

        dropped = total_passwords - remaining
        result_value = remaining

        emails_with_remaining = sorted(
            data["email"] for data in per_email.values() if data["kept"]
        )

        siemplify.result.add_result_json(
            {
                "case_id": str(getattr(siemplify, "case_id", "") or ""),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "policy": {
                    "minimum_length": minimum_length,
                    "require_symbol": require_symbol,
                },
                "total_passwords": total_passwords,
                "remaining": remaining,
                "dropped": dropped,
                "emails_with_remaining_passwords": emails_with_remaining,
                "results_by_email": list(per_email.values()),
            }
        )

        if total_passwords == 0:
            output_message = (
                "No plaintext passwords were present on the case events. "
                "Ensure the connector's 'Include Plaintext Secrets' option is "
                "enabled if a reset decision requires the raw values."
            )
        elif remaining > 0:
            output_message = (
                f"{remaining} of {total_passwords} exposed password(s) match the "
                f"configured policy (minimum length {minimum_length}, "
                f"require symbol {require_symbol}); {dropped} dropped."
            )
        else:
            output_message = (
                f"All {total_passwords} exposed password(s) were dropped by the "
                f"configured policy (minimum length {minimum_length}, "
                f"require symbol {require_symbol}); no reset required."
            )

    except Exception as error:
        siemplify.LOGGER.error(f'Error executing action "{SCRIPT_NAME}". Reason: {error}')
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = 0
        output_message = f'Error executing action "{SCRIPT_NAME}". Reason: {error}'

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"status: {status}, result_value: {result_value}, output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
