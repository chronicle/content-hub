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

"""Analyze the email-security posture of a domain's published DNS records.

Runs checkdmarc against a domain and reports the deployment state of its SPF,
DMARC, and MX records and DNSSEC, in the same structures the Analyze Headers
action emitted before integration version 53.0. These fields describe what the
domain publishes and enforces; they say nothing about whether any individual
email passed authentication — use Analyze Headers or Analyze EML Headers for
per-message verdicts.
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

    The SPF, DMARC, MX, and DNSSec structures are passed through verbatim as
    checkdmarc produced them (the same shapes Analyze Headers emitted before
    integration version 53.0). StrongSPF keeps that action's old semantics:
    True when the domain's SPF policy for non-matching senders is a hard or
    soft fail ("-all" or "~all").

    Args:
        domain: The domain that was checked.
        domain_check: Single-domain output of ``checkdmarc.check_domains``.

    Returns:
        The action's JSON result.
    """
    spf = domain_check.get("spf")
    result = {
        "Domain": domain,
        "SPF": spf,
        "DMARC": domain_check.get("dmarc"),
        "MX": domain_check.get("mx"),
        "DNSSec": domain_check.get("dnssec"),
        "StrongSPF": False,
    }
    try:
        result["StrongSPF"] = spf["parsed"]["all"] in ("fail", "softfail")
    except (KeyError, TypeError):
        try:
            result["StrongSPF"] = spf["record"].strip().endswith(("-all", "~all"))
        except (AttributeError, KeyError, TypeError):
            pass
    return result


@output_handler
def main() -> None:
    """Check the domain's published DNS records and emit the result JSON."""
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    domain = siemplify.extract_action_param("Domain", print_value=True)
    test_tls = siemplify.extract_action_param(
        "Test MX Hosts For STARTTLS/TLS",
        input_type=bool,
        default_value=False,
    )
    include_tag_descriptions = siemplify.extract_action_param(
        "Include Tag Descriptions",
        input_type=bool,
        default_value=True,
    )

    status = EXECUTION_STATE_COMPLETED
    result_value = "true"
    try:
        domain = str(domain or "").strip().lower()
        if not domain:
            raise ValueError('the "Domain" parameter must not be empty')
        domain_check = checkdmarc.check_domains(
            [domain],
            skip_tls=not test_tls,
            include_tag_descriptions=include_tag_descriptions,
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
