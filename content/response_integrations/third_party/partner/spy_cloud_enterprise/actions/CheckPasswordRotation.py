"""
SpyCloud Enterprise - Check Password Rotation

Decides whether a case's exposed credentials are still live, so the password
response playbooks can skip a reset the user has already performed themselves.

An exposed password only matters while the account still uses it. If the identity
provider changed the password *after* SpyCloud published the exposure, the leaked
value is already dead and resetting again only burns the user's session for no
security gain. This action compares the two timestamps:

  - Last Password Reset Time: taken from the IdP (Okta ``passwordChanged`` /
    Entra ID ``lastPasswordChangeDateTime``), supplied by the preceding
    get-user step in the playbook.
  - The latest publish date across the case's SpyCloud password exposures,
    read from the events the connector already flattened onto the case.

``result_value`` is 1 when a reset is still warranted and 0 when the password was
already rotated after the newest exposure, so the playbook can gate the reset on
``ScriptResult > 0``.

Unknown means reset. A missing or unparseable IdP timestamp, or a case with no
datable password exposure, returns 1 - the safe direction is to remediate an
exposure we cannot prove is stale.

Data source: this action does NOT call the SpyCloud API. It reads the exposures
already attached to the case, exactly like Filter Passwords By Policy.

Sensitive data: no password value is read or surfaced. The JSON result carries
only timestamps, counts, and the decision.
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
from ..core.Constants import CHECK_PASSWORD_ROTATION_SCRIPT_NAME

SCRIPT_NAME = CHECK_PASSWORD_ROTATION_SCRIPT_NAME

LAST_RESET_PARAM = "Last Password Reset Time"
EMAIL_PARAM = "Email"
PASSWORD_EXPOSURES_ONLY_PARAM = "Password Exposures Only"
DEFAULT_PASSWORD_EXPOSURES_ONLY = True

RESET_NEEDED = 1
RESET_NOT_NEEDED = 0


def _event_has_password(props: dict) -> bool:
    """Report whether an exposure event involves a password at all.

    Unlike Filter Passwords By Policy this does not require the plaintext value:
    the connector's boolean flags are enough to know a password was exposed, and
    they are present whether or not secret retention was enabled.
    """
    if datamodels.collect_plaintext_passwords(props):
        return True
    return any(
        str(props.get(key, "")).strip().lower() in ("true", "yes", "1", "t")
        for key in ("spycloud_has_plaintext_password", "spycloud_has_password")
    )


@output_handler
def main() -> None:
    """Compare the IdP's last password change against the case's exposure dates."""
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = RESET_NEEDED
    output_message = ""

    try:
        last_reset_raw = siemplify.extract_action_param(
            param_name=LAST_RESET_PARAM,
            is_mandatory=False,
            print_value=True,
        )
        email_filter = siemplify.extract_action_param(
            param_name=EMAIL_PARAM,
            is_mandatory=False,
            print_value=True,
        )
        password_exposures_only = siemplify.extract_action_param(
            param_name=PASSWORD_EXPOSURES_ONLY_PARAM,
            is_mandatory=False,
            input_type=bool,
            default_value=DEFAULT_PASSWORD_EXPOSURES_ONLY,
            print_value=True,
        )

        email_filter = str(email_filter or "").strip().lower()
        last_reset = datamodels.parse_timestamp(last_reset_raw)

        # Walk the case's SpyCloud events and keep the newest publish date among
        # the exposures this decision is about.
        latest_publish: datetime | None = None
        latest_publish_raw = ""
        considered = 0
        undated = 0

        alerts = siemplify.case.alerts or []
        siemplify.LOGGER.info(f"Scanning {len(alerts)} alert(s) in the case")

        for alert in alerts:
            for event in getattr(alert, "security_events", []) or []:
                props = getattr(event, "additional_properties", {}) or {}
                if not datamodels.is_spycloud_event(props):
                    continue
                if password_exposures_only and not _event_has_password(props):
                    continue
                if email_filter:
                    email = str(props.get("spycloud_email", "") or "").strip().lower()
                    if email != email_filter:
                        continue
                considered += 1
                raw_date = datamodels.event_publish_date(props)
                published = datamodels.parse_timestamp(raw_date)
                if published is None:
                    undated += 1
                    continue
                if latest_publish is None or published > latest_publish:
                    latest_publish = published
                    latest_publish_raw = raw_date

        # Decide, defaulting to "reset" whenever the comparison cannot be made.
        if last_reset is None:
            rotated = False
            reason = (
                "no usable last password reset time was supplied, so the exposure "
                "is treated as live"
            )
        elif latest_publish is None:
            rotated = False
            reason = (
                "no SpyCloud exposure on this case carries a publish date to "
                "compare against, so the exposure is treated as live"
            )
        elif last_reset > latest_publish:
            rotated = True
            reason = (
                "the password was changed after the most recent exposure was "
                "published, so the exposed credential is already dead"
            )
        else:
            rotated = False
            reason = (
                "the most recent exposure was published at or after the last "
                "password change, so the exposed credential may still be live"
            )

        result_value = RESET_NOT_NEEDED if rotated else RESET_NEEDED

        siemplify.result.add_result_json(
            {
                "case_id": str(getattr(siemplify, "case_id", "") or ""),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "email_filter": email_filter,
                "password_exposures_only": password_exposures_only,
                "last_password_reset": last_reset.isoformat() if last_reset else "",
                "last_password_reset_raw": str(last_reset_raw or ""),
                "latest_exposure_publish_date": (
                    latest_publish.isoformat() if latest_publish else ""
                ),
                "latest_exposure_publish_date_raw": latest_publish_raw,
                "exposures_considered": considered,
                "exposures_without_publish_date": undated,
                "password_already_rotated": rotated,
                "reset_required": not rotated,
                "reason": reason,
            }
        )

        if rotated:
            output_message = (
                f"No reset required: {reason}. Last password change "
                f"{last_reset.isoformat()} is newer than the latest exposure "
                f"published {latest_publish.isoformat()} "
                f"({considered} exposure(s) considered)."
            )
        else:
            output_message = (
                f"Reset required: {reason} ({considered} exposure(s) considered)."
            )

    except Exception as error:
        siemplify.LOGGER.error(f'Error executing action "{SCRIPT_NAME}". Reason: {error}')
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        # Fail toward remediation: an error here must not silently cancel a reset.
        result_value = RESET_NEEDED
        output_message = f'Error executing action "{SCRIPT_NAME}". Reason: {error}'

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"status: {status}, result_value: {result_value}, output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
