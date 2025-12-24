from __future__ import annotations

from greynoise import GreyNoise
from greynoise.exceptions import RateLimitError, RequestFailure
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler

from ..core.constants import USER_AGENT

INTEGRATION_NAME = "GreyNoise"

SCRIPT_NAME = "IP Timeline Lookup"


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

    days = siemplify.extract_action_param(
        param_name="days",
        default_value="30",
        is_mandatory=False,
        print_value=True,
    )
    try:
        days = int(days)
    except:
        siemplify.LOGGER.info("Days does not appear to be a valid value")
        output_message = "Days does not appear to be a valid value"
        result_value = False
        status = EXECUTION_STATE_FAILED

    limit = siemplify.extract_action_param(
        param_name="limit",
        default_value="50",
        is_mandatory=False,
        print_value=True,
    )
    try:
        limit = int(limit)
    except:
        siemplify.LOGGER.info("Limit does not appear to be a valid value")
        output_message = "Limit does not appear to be a valid value"
        result_value = False
        status = EXECUTION_STATE_FAILED

    output_message = "Successfully processed:"
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_json = {}
    invalid_ips = []
    for ipaddr in ips:
        siemplify.LOGGER.info(f"Started processing IP: {ipaddr}")

        try:
            res = session.timelinedaily(ipaddr, days=days, limit=limit)

            if "activity" in res and len(res["activity"]) >= 1:
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
                output["message"] = "Address has no timeline events."
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
        "<tr><td style='text-align: left;'><strong style='font-size: 17px'>"
        "Daily Internet Scanning Activies</span></strong></td>"
    )
    content += "</tbody></table><br>"
    content += (
        "<table style='100%'; border='1'; cellpadding='5'; cellspacing='5'><tbody>"
    )
    content += (
        "<tr><th style='text-align:left'>Date</th><th style='text-align:left'>"
        "Classification</th><th style='text-align:left'>Tags</th></tr>"
    )
    for item in self["activity"][:10]:
        tag_list = []
        for tag in item["tags"]:
            tag_list.append(tag["name"])
        content += f"<tr><td width='25%'>{item['timestamp'].split('T')[0]}</td><td width='30%'>{item['classification']}</td><td>{', '.join(tag_list)}</td></tr>"
    content += "</tbody></table><br>"
    content += "<p>Only first 10 matches are displayed</p><br><br>"
    content += (
        '<p><strong>More Info: <a target="_blank" href=https://viz.greynoise.io/ip/'
        "{ip}?view=timeline>https://viz.greynoise.io/ip/{ip}?view=timeline</a></strong>&nbsp; </p>".format(
            ip=self["ip"],
        )
    )
    return content


if __name__ == "__main__":
    main()
