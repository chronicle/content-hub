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
    base_id = siemplify.parameters["Base Id"]
    table_name = siemplify.parameters["Table name"]
    max_records = siemplify.parameters["Max Records"]
    sort_by = siemplify.parameters["Sort by"]
    sort_direction = siemplify.parameters["Sort Direction"]
    airtable = Airtable(base_id, table_name, api_key)

    sort_direction_value = "desc"
    if sort_direction == "Ascending":
        sort_direction_value = "asc"
    if sort_by:
        results = airtable.get_all(
            maxRecords=max_records,
            sort=[(sort_by, sort_direction_value)],
        )
    else:
        results = airtable.get_all(maxRecords=max_records)

    records_count = len(results)
    print(json.dumps(results))
    siemplify.result.add_result_json(json.dumps(results))
    siemplify.result.add_json("Search Results", json.dumps(results))
    output_message = (
        f"{records_count} records from table {table_name} were fetched successfully."
    )
    siemplify.end(output_message, records_count)


if __name__ == "__main__":
    main()
