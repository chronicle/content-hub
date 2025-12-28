from __future__ import annotations

import json

from airtable import Airtable
from soar_sdk.SiemplifyAction import SiemplifyAction

INTEGRATION_NAME = "AirTable"


def main():
    siemplify = SiemplifyAction()

    api_key = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME,
        param_name="Api key",
    )
    base_id = siemplify.parameters["Base id"]
    table_name = siemplify.parameters["Table name"]
    field_name = str(siemplify.parameters["Field name"])
    json_fields_str = siemplify.parameters["Json fields"]

    results = []

    json_fields_dict = json.loads(json_fields_str)
    airtable = Airtable(base_id, table_name, api_key)

    updated_count = 0
    inserted_count = 0
    for json_fields_item in json_fields_dict:
        results = airtable.search(field_name, json_fields_item[field_name])
        if len(results) != 0:
            for result in results:
                record_id = result["id"]
                updated_count = updated_count + 1
                airtable.update(record_id, json_fields_item)
        else:
            inserted_count = inserted_count + 1
            res = airtable.insert(json_fields_item)

    records_count = len(results)

    output_message = (
        f"{inserted_count} records were inserted, {updated_count} records were updated."
    )
    siemplify.end(output_message, inserted_count + updated_count)


if __name__ == "__main__":
    main()
