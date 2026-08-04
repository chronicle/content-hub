# Censys Integration — Change Analysis Document

**Date:** June 12, 2026
**Integration:** Censys | **Type:** Enhancement

---

## 1. Overview

Censys has introduced a new enrichment endpoint for host/IP data that returns a richer, more focused response compared to the previous endpoint. This document captures the changes required and the impact on existing functionality.

---

## 2. New Action — Enrich Host

| | Old (`Enrich IPs`) | New (`Enrich Host`) |
|---|---|---|
| **Endpoint** | `POST /v3/global/asset/host` | `GET /v3/global/asset/enrichment/host/{ip}` |
| **How it works** | Single batch call with all IPs | One API call per IP (loop) |
| **At Time param** | Supported | Not supported by new API |
| **Response** | Array of results | Single resource per call |

**Key decisions:**
- The old `Enrich IPs` action **stays intact** — no changes, no regression risk
- A new `Enrich Host` action is added alongside it
- Since the new endpoint is per-IP only, the action loops through each IP entity individually

---

## 3. Playbook Update

The existing **Censys Entity Enrichment** playbook currently uses `Enrich IPs`. It will be updated to use the new `Enrich Host` action instead.

- The `At Time` parameter currently passed in the playbook step will be removed (not supported by new endpoint)
- No other playbook steps are affected

---

## 4. Enrichment Field Analysis

### 4.1 Fields No Longer Available — Will Be Dropped

These fields were previously enriched on the IP entity but are **no longer present in the new API response**.

| Enrichment Field | Previously Mapped From |
|---|---|
| `Censys_transport_protocols` | Service transport protocol (TCP/UDP) |
| `Censys_vulnerabilities` | Known CVEs per service |
| `Censys_last_scan_time` | Last time service was scanned |

> These 3 fields will not be populated by the new action. Existing entity data from the old action will be cleared when the new action runs.

---

### 4.2 Fields That Stay the Same

These fields are present in both old and new responses — **no change to enrichment logic**.

| Enrichment Field | Data |
|---|---|
| `Censys_service_count` | Total number of exposed services |
| `Censys_ports` | Open ports |
| `Censys_protocols` | Service protocols |
| `Censys_host_labels` | Host classification labels |
| `Censys_service_labels` | Per-service labels |
| `Censys_threat_names` | Threat names on services |
| `Censys_dns_names` | DNS names |
| `Censys_reverse_dns` | Reverse DNS names |
| `Censys_network_name` | WHOIS network name |
| `Censys_network_cidrs` | Network CIDRs |
| `Censys_asn_name` / `Censys_asn_id` | ASN info |
| `Censys_location_*` | City, province, postal, country |
| `Censys_country_code` / `Censys_continent` | Country & continent |
| `Censys_geo_lat` / `Censys_geo_long` | Coordinates |

---

### 4.3 New Fields — Available for First Time

These fields are **new in the enrichment endpoint** and were not available before. Recommended to include in the new action's enrichment.

| Enrichment Field | Data | Value |
|---|---|---|
| `Censys_reputation_score` | Numeric risk score for the IP | High |
| `Censys_reputation_score_level` | Categorical level (e.g. malicious / suspicious / benign) | High |
| `Censys_greynoise_classification` | GreyNoise classification (malicious / benign / unknown) | High |
| `Censys_greynoise_actor` | Known threat actor name from GreyNoise | Medium |
| `Censys_greynoise_last_observed` | Last time seen by GreyNoise | Medium |
| `Censys_privacy_tor` | Is TOR exit node (true/false) | High |
| `Censys_privacy_vpn` | Is VPN (true/false) | High |
| `Censys_privacy_proxy` | Is proxy (true/false) | High |
| `Censys_privacy_anonymous` | Is anonymous (true/false) | Medium |
| `Censys_privacy_relay` | Is a relay (true/false) | Medium |

> **Network flags** (`hosting`, `mobile`, `satellite`) and **detailed threat actor/malware data** are also available but considered optional — to be confirmed with Censys/product team based on analyst needs.

---

## 5. Effort Estimate

| Area | Scope | Effort |
|---|---|---|
| New `Enrich Host` action | New action file, YAML definition, example output, AI description | ~1 day |
| Core layer updates | Constants, API manager method, new enrichment data model with new/dropped fields | ~1 day |
| Playbook update | Swap action reference, remove `At Time` param | ~0.5 day |
| Testing & QA | Unit tests for new action, end-to-end validation, regression check on old action | ~1.5 days |
| **Total** | | **~4 days** |

---

## 6. What Stays Unchanged

- `Enrich IPs` action — no modifications
- All other actions (Enrich Web Properties, Enrich Certificates, Get Host History, etc.)
- Integration configuration (API Key, Organization ID, Verify SSL)
- All existing enrichment field keys that map correctly to the new response

---

*Note: Effort estimates are approximate. Final timeline subject to review and sign-off.*
