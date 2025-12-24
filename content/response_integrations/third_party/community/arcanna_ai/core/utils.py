from __future__ import annotations


def fetch_field_value(input_json, id_field):
    if not id_field:
        return None
    id_field_parts = id_field.split(".")
    event_id = input_json
    for tok in id_field_parts:
        event_id = event_id.get(tok)
    return event_id
