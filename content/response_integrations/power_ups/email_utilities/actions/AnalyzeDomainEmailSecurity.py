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

"""Analyze the email-security posture of a domain's published records.

Runs checkdmarc against a domain and reports the deployment state of its SPF,
DMARC, and MX records, DNSSEC, MTA-STS, SMTP TLS reporting (TLS-RPT), and
BIMI. The SPF/DMARC/MX/DNSSec structures match what the Analyze Headers action
emitted before integration version 53.0. These fields describe what the domain
publishes and enforces; they say nothing about whether any individual email
passed authentication — use Analyze Headers or Analyze EML Headers for
per-message verdicts.

The action only reads published state (DNS lookups, plus the HTTPS fetches
checkdmarc uses for MTA-STS policies and BIMI assets). It never connects to
the domain's MX hosts over SMTP: such STARTTLS/TLS probing is blocked in many
runtimes (Google Cloud blocks destination TCP port 25), where each probe would
time out and then record a misleading "STARTTLS is not supported" warning.
"""

from __future__ import annotations

import checkdmarc
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

SCRIPT_NAME = "Analyze Domain Email Security"


def build_result(domain: str, domain_check: dict) -> dict:
    """Assemble the action's JSON result from checkdmarc output.

    Every checkdmarc section is passed through verbatim: SPF, DMARC, MX, and
    DNSSec keep the shapes Analyze Headers emitted before integration version
    53.0, and MTASTS, SMTPTLSReporting, and BIMI expose the rest of the
    email-security checks checkdmarc performs. The pre-53.0 StrongSPF boolean
    is deliberately not reproduced: it is not a standard concept and gave a
    false sense of security. The policy it summarized is available verbatim as
    ``SPF.parsed.all`` (e.g. "fail" for "-all", "softfail" for "~all").

    Args:
        domain: The domain that was checked.
        domain_check: Single-domain output of ``checkdmarc.check_domains``.

    Returns:
        The action's JSON result.
    """
    return {
        "Domain": domain,
        "SPF": domain_check.get("spf"),
        "DMARC": domain_check.get("dmarc"),
        "MX": domain_check.get("mx"),
        "DNSSec": domain_check.get("dnssec"),
        "MTASTS": domain_check.get("mta_sts"),
        "SMTPTLSReporting": domain_check.get("smtp_tls_reporting"),
        "BIMI": domain_check.get("bimi"),
    }


@output_handler
def main() -> None:
    """Check the domain's published DNS records and emit the result JSON."""
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    domain = siemplify.extract_action_param("Domain", print_value=True)
    include_tag_descriptions = siemplify.extract_action_param(
        "Include Tag Descriptions",
        input_type=bool,
        default_value=True,
    )
    bimi_selector = siemplify.extract_action_param(
        "BIMI Selector",
        default_value="default",
    )

    status = EXECUTION_STATE_COMPLETED
    result_value = "true"
    try:
        domain = str(domain or "").strip().lower()
        if not domain:
            raise ValueError('the "Domain" parameter must not be empty')
        # check_mx_tls is left at its default of False: the action never probes
        # MX hosts over SMTP (see the module docstring).
        domain_check = checkdmarc.check_domains(
            [domain],
            include_tag_descriptions=include_tag_descriptions,
            bimi_selector=str(bimi_selector or "default").strip() or "default",
        )
        result = build_result(domain, domain_check)
        siemplify.result.add_result_json(result)
        valid_spf = bool((result["SPF"] or {}).get("valid"))
        valid_dmarc = bool((result["DMARC"] or {}).get("valid"))
        result_value = "true" if valid_spf and valid_dmarc else "false"
        output_message = (
            f"Checked the published email-security DNS records of {domain}. "
            f"Valid SPF record: {valid_spf}. Valid DMARC record: {valid_dmarc}."
        )
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Failed to analyze domain email security: {e}"
        siemplify.LOGGER.error(output_message)

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
