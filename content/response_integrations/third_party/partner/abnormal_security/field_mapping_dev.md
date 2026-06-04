# Abnormal Security Field Mapping Dev

> EXAMPLE: @field_mapping_dev.md add a new threat-scoped action that pre-fills from the SIEM event

This integration spans three layers that must agree on field names. When adding
or changing an action parameter, verify the placeholder, the event body, and the
API input line up — a mismatch fails silently (empty field) or corrupts data
(precision loss).

## The three layers

1. **Event body** — what lands in the SOAR case, referenced by action
   `default_value` placeholders as `[Event.event_extracted_event.abx_body.<field>]`.
2. **Action parameter** — the `default_value` placeholder in each `actions/*.yaml`.
3. **API input** — what the manager method in `core/AbnormalManager.py` sends to
   the Abnormal API.

## Event body is snake_case and threat-centric

The SIEM event body (`abx_body`) is produced by `SiemMessageEvent` —
source of truth: `src/py/abnormal/siem_integrations/siem_events.py` in the main
monorepo (search for `class SiemMessageEvent`). List the exact fields with:

```bash
sed -n '/class SiemMessageEvent/,/def get_siem_data/p' \
  $SOURCE/src/py/abnormal/siem_integrations/siem_events.py
```

Two consequences that drive placeholder choices:

- **Fields are snake_case** (`threat_id`, `from_address`, `received_time`), not
  the camelCase of the REST API responses (`threatId`, `fromAddress`). Placeholders
  must use snake_case.
- **There is no `case_id`.** SIEM events describe threats/messages only. Abnormal
  Cases (Account Takeover / abuse-mailbox) are a separate resource and never appear
  in the SIEM threat-log stream.

## Message IDs: always use the string form

`abx_body` carries both `abx_message_id` and `abx_message_id_str`. Always reference
`abx_message_id_str`. The numeric `abx_message_id` is a 64-bit integer that the SOAR
placeholder engine renders as a float (e.g. `-1.08e+18`), losing precision — the ID
is then unusable against the API.

## Layer compatibility map

| Action group | Placeholder field | API input (`core/AbnormalManager.py`) |
|---|---|---|
| Threat (Get/Post/Remediate/Unremediate Threat, Attachments, Links) | `abx_body.threat_id` | `threat_id` (UUID) on `/v1/threats/{id}` |
| Threat "Message IDs" param | `abx_body.abx_message_id_str` | message id list |
| Search & Respond (Delete/Move/Remediate/SubmitD360) | none — Search Messages output | full message objects on `/v1/search/remediate` |
| Case (Get/Post/Resolve/Mark×3) | none — manual entry | `case_id` on `/v1/cases/{id}` |

## Search & Respond requires full message objects

The remediate request body is the `MessageToRemediate` model in
`src/py/abnormal/apps/soar_search_and_respond/models.py`. Required fields (Pydantic
`Field(...)`): `tenant_id`, `raw_message_id`, `mailbox_name`, `native_user_id`,
`subject`, `sender`, `received_time`. `abnormal_message_id` is *optional* — the Abnormal
ID alone does not satisfy the schema.

`raw_message_id` is the **native mail-system ID** (e.g. Graph/EWS `AAMkAGI2THVSAAA=`),
which only exists in a `SearchResult` (the `SearchMessages` output) — **not** in the
SIEM threat event. The event's `internet_message_id` (`<msg@host>`) is a different field
the remediate model does not accept. Therefore Delete/Move/Remediate/SubmitD360 Messages
**cannot be built from a threat event** and must be chained from `Search Messages`, whose
`SearchResult` fields map 1:1 to `MessageToRemediate`.

`parse_messages_input` in `core/AbnormalManager.py` accepts only a JSON array or a single
JSON object; any bare ID raises with guidance to chain Search Messages, or to use
**Remediate Threat** (`/v1/threats/{id}`) for single-message remediation.

`SearchMessages` reads the API's `results` key (the `SearchResult` list), not `messages`.

## Why case actions do not auto-fill

Case actions target Abnormal Cases, which the SIEM event body does not contain. Their
`Case ID` parameter defaults to empty: the analyst enters the ID directly or chains it
from a `List Cases` / `Get Case` step. Do not add an `abx_body.case_id` placeholder —
it resolves to nothing.

## Ontology mapping vs SIEM events

`ontology_mapping.yaml` extracts SOAR entities from events produced by *this
integration's connector* (`AbnormalSecurityConnector`), whose events are camelCase
(`dict_to_flat` of the REST response), with snake_case secondary match terms. It does
**not** govern SIEM-originated cases — those use Chronicle's own parser/UDM mapping.
Keep the camelCase primary match terms aligned with the connector's event field names.
