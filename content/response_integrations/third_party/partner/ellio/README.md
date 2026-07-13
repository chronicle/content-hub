# ELLIO - Google SecOps SOAR integration

Enriches IP entities with ELLIO threat intelligence, classifies them against ELLIO Common
Business Services, and pushes confirmed-bad IPs to ELLIO Blocklist Automation (EDL).

## Actions

| Action | Purpose |
|---|---|
| `Ping` | Validate connectivity and credentials. |
| `Enrich IP` | Write `ELLIO_*` threat context onto IP entities, add an insight card, return a recommended case priority. |
| `CBS Lookup` | Classify IPs against Common Business Services (cloud / CDN / SaaS); write `ELLIO_CBS_*` provider/type/service/region/cidr context and add an insight card. |
| `Add IP to Blocklist` | Push IPs to a Blocklist Automation ruleset (needs a `read_write` key). |

Only public, globally-routable IPs are processed; private, reserved, and SOAR-internal
addresses are skipped and reported.

## Enrich IP

Writes classification, tags, CVEs, rDNS, country, first/last seen, MuonFP/JA3/JA4
fingerprints, and observed ports / HTTP paths / user-agents onto the entity; malicious and
promiscuous IPs are marked suspicious. `seen:false` from the API means the IP is not
tracked by ELLIO.

The script result `recommended_priority` is `High` when a malicious IP was found, otherwise
`None`. The action never changes the case priority; a playbook applies the recommendation
via the built-in Change Priority action.

## Add IP to Blocklist

The rule name is auto-built as parsable case context
(`secops_case=<id> | alert=<name> | ellio=<classification>`). A read-only key fails with
403. `Expires In Days` set to 0 creates a permanent rule.

## Configuration

| Parameter | |
|---|---|
| API Root | `https://api.ellio.tech` |
| API Key | `read` covers Enrich IP and CBS Lookup; Add IP to Blocklist needs `read_write` |
| Blocklist Ruleset ID | target ruleset for Add IP to Blocklist |
| Verify SSL | keep enabled |

## Playbook wiring (enrich -> priority)

1. **ELLIO > Enrich IP** on the alert's IP Address entities.
2. Branch on `recommended_priority`: `High` -> built-in **Change Priority -> High**,
   optionally **Add IP to Blocklist** behind a human-approval step; `None` -> leave the
   priority untouched and use the `ELLIO_*` context for triage.

## Build

Python 3.11; depends on `requests`, `TIPCommon`, `EnvironmentCommon` (content-hub wheels).
Validate and pack with the `mp` CLI: `mp validate -i ellio`, `mp test -i ellio`,
`mp pack integration ELLIO`.
