from __future__ import annotations

from greynoise import GreyNoise
from greynoise.exceptions import RateLimitError, RequestFailure
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler

from ..core.constants import USER_AGENT

INTEGRATION_NAME = "GreyNoise"

SCRIPT_NAME = "RIOT IP Lookup"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    api_key = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME,
        param_name="GN API Key",
    )

    session = GreyNoise(api_key=api_key, integration_name=USER_AGENT)

    ips = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.ADDRESS
    ]

    output_message = "Successfully processed:"
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_json = {}
    invalid_ips = []
    for ipaddr in ips:
        siemplify.LOGGER.info(f"Started processing IP: {ipaddr}")

        try:
            res = session.riot(ipaddr)

            if res["riot"]:
                siemplify.result.add_json(str(ipaddr), res)
                output = res
                output_json[str(ipaddr)] = output
                siemplify.add_entity_insight(
                    ipaddr,
                    to_insight(output),
                    triggered_by=INTEGRATION_NAME,
                )

                output_message = output_message + f" {ipaddr},"
            else:
                output = res
                output["message"] = (
                    "Address is not associated with a known Common Business Service."
                )
                siemplify.result.add_json(str(ipaddr), output)

            output_json[str(ipaddr)] = output

        except ValueError:
            siemplify.LOGGER.info(f"Invalid Routable IP: {ipaddr}")
            invalid_ips.append(ipaddr)
            continue

        except RequestFailure:
            siemplify.LOGGER.info("Unable to auth, please check API Key")
            output_message = "Unable to auth, please check API Key"
            result_value = False
            status = EXECUTION_STATE_FAILED
            break

        except RateLimitError:
            siemplify.LOGGER.info("Daily rate limit reached, please check API Key")
            output_message = "Daily rate limit reached, please check API Key"
            result_value = False
            status = EXECUTION_STATE_FAILED
            break

        except Exception as e:
            siemplify.LOGGER.info(e)
            siemplify.LOGGER.info("Unknown Error Occurred")
            output_message = "Unknown Error Occurred"
            result_value = False
            status = EXECUTION_STATE_FAILED
            break

    if output_json:
        siemplify.result.add_result_json(
            {"results": convert_dict_to_json_result_dict(output_json)},
        )

    if invalid_ips and result_value:
        invalid_ips_string = ""
        for item in invalid_ips:
            if invalid_ips_string == "":
                invalid_ips_string = str(item)
            else:
                invalid_ips_string = invalid_ips_string + ", " + str(item)
        output_message = output_message + f" Invalid IPs skipped: {invalid_ips_string}"

    siemplify.end(output_message, result_value, status)


def to_insight(self):
    content = ""
    content += "<table style='100%'><tbody>"
    content += (
        "<tr><td style='text-align: left; width: 30%;'><strong style='font-size: 17px;"
        "color:#7CFC00'><span>Benign Service</span></strong></td>"
    )
    content += "</tbody></table><br>"
    content += (
        "<p>This IP is from a known harmless services and/or organizations and can "
        "most likely be trusted.</p></br>"
    )
    content += "<table style='100%'><tbody>"
    content += (
        "<tr><td style='text-align: left; width: 30%;'><strong>Name: </strong></td>"
        "<td style='text-align: left; width: 30%;'>{name}</td></tr>".format(
            name=self["name"],
        )
    )
    content += (
        "<tr><td style='text-align: left; width: 30%;'><strong>Category: </strong></td>"
        "<td style='text-align: left; width: 30%;'>{category}</td></tr>".format(
            category=self["category"],
        )
    )
    content += (
        "<tr><td style='text-align: left; width: 30%;'><strong>Last Updated: </strong>"
        "</td><td style='text-align: left; width: 30%;'>{last_updated}</td></tr>".format(
            last_updated=self["last_updated"],
        )
    )
    content += (
        "<tr><td style='text-align: left; width: 30%;'><strong>Explanation: </strong>"
        "</td><td style='text-align: left; width: 30%;'>{explanation}</td></tr>".format(
            explanation=self["explanation"],
        )
    )
    content += "</tbody></table><br><br>"
    content += (
        '<p><strong>More Info: <a target="_blank" href=https://viz.greynoise.io/riot/'
        "{ip}>https://viz.greynoise.io/riot/{ip}</a></strong>&nbsp; </p>".format(
            ip=self["ip"],
        )
    )
    return content


if __name__ == "__main__":
    main()
