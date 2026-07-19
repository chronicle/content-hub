"""Shared constants for the ELLIO SOAR integration."""
from __future__ import annotations

INTEGRATION_NAME = "ELLIO"
INTEGRATION_VERSION = "1.0"  # keep in sync with pyproject.toml + release_notes.yaml

DEFAULT_ELLIO_API_ROOT = "https://api.ellio.tech"  # docs.ellio.tech/api-reference
# CTI extended lookup: GET /v1/cti/extended_lookup/{ip}; auth header X-API-Key.
# EDL blocklist add:   POST /v1/edl/ip-rulesets/{ruleset_id}/rules
#   body {ip, name, conflict_resolution[extend|override|skip|fail], expires_in_days}.
# EDL check:           POST /v1/edl/ip-rulesets/{ruleset_id}/rules:check  body {ip}.

REQUEST_TIMEOUT = 30

# CBS classification: GET /v1/cbs/lookup?ip=<ip> (same X-API-Key).
# Prefix for CBS entity-enrichment keys (distinct from threat ENRICH_PREFIX).
CBS_ENRICH_PREFIX = "ELLIO_CBS_"

# ELLIO classification -> recommended SecOps case priority. Only a malicious verdict
# recommends a priority (-> High); promiscuous/unknown/benign are context and leave the
# case priority untouched (no recommendation). The Enrich IP action returns this
# recommendation only - it never sets the case priority itself.
CLASSIFICATION_PRIORITY = {"malicious": "High"}

# Prefix for entity enrichment keys written back onto the SOAR entity.
ENRICH_PREFIX = "ELLIO_"
