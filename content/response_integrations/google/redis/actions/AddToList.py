from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.RedisManager import RedisManager
import json


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("Redis")
    server = conf["Server Address"]
    port = int(conf["Port"])

    redis_manager = RedisManager(server, port, 0)
    # Redis Lists are simply lists of strings, sorted by insertion order.
    list_name = siemplify.parameters["List Name"]
    value = siemplify.parameters["Value"]
    json_results = {}

    is_set = redis_manager.add_to_list(list_name, value)

    list_values = redis_manager.get_list(list_name)
    if list_values:
        json_results = json.dumps(list_values)
    # output_message = "Successfully add {value} to {list}.".format(value=value, list=list_name)
    output_message = "Successfully add value to list"

    # add json
    siemplify.result.add_result_json(json_results)
    siemplify.end(output_message, True)


if __name__ == "__main__":
    main()
