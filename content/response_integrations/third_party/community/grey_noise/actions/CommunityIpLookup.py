from __future__ import annotations

from greynoise import GreyNoise
from greynoise.exceptions import RateLimitError, RequestFailure
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler

from ..core.constants import COMMUNITY_USER_AGENT

INTEGRATION_NAME = "GreyNoise"

SCRIPT_NAME = "Community IP Lookup"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    api_key = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME,
        param_name="GN API Key",
    )

    session = GreyNoise(
        api_key=api_key,
        integration_name=COMMUNITY_USER_AGENT,
        offering="community",
    )

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
            res = session.ip(ipaddr)

            if res and res["noise"]:
                siemplify.result.add_json(str(ipaddr), res)
                output = res
                output_json[str(ipaddr)] = output
                siemplify.add_entity_insight(
                    ipaddr,
                    to_noise_insight(output),
                    triggered_by=INTEGRATION_NAME,
                )
                output_message = output_message + f" {ipaddr},"

            elif res and res["riot"]:
                siemplify.result.add_json(str(ipaddr), res)
                output = res
                output_json[str(ipaddr)] = output
                siemplify.add_entity_insight(
                    ipaddr,
                    to_riot_insight(output),
                    triggered_by=INTEGRATION_NAME,
                )

                output_message = output_message + f" {ipaddr},"

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


def to_noise_insight(self):
    content = ""
    content += "<table style='100%'><tbody>"
    content += (
        "<tr><td style='text-align: left; width: 30%;'><strong style='font-size: 17px'>"
        "Noise: <span>{noise}</span></strong></td>".format(noise=self["noise"])
    )
    content += "</tbody></table><br>"
    content += (
        "<p>This IP has been observed opportunistically scanning the internet "
        "and is not directly targeting your organization.</p></br>"
    )
    content += "<table style='100%'><tbody>"
    if self["classification"] == "malicious":
        content += (
            "<tr><td style='text-align: left; width: 30%; color: red'><strong>"
            "Classification: </strong></td><td style='text-align: left; width: 30%; "
            "color: red'>{classification}</td>"
            "</tr>".format(classification=self["classification"])
        )
    elif self["classification"] == "benign":
        content += (
            "<tr><td style='text-align: left; width: 30%; color: #1dbf11'><strong>"
            "Classification: </strong></td><td style='text-align: left; width: 30%;"
            " color: #1dbf11'>{classification}</td>"
            "</tr>".format(classification=self["classification"])
        )
    else:
        content += (
            "<tr><td style='text-align: left; width: 30%;'><strong>Classification: "
            "</strong></td><td style='text-align: left; width: 30%;'>{classification}"
            "</td></tr>".format(classification=self["classification"])
        )
    content += (
        "<tr><td style='text-align: left; width: 30%;'><strong>Name: </strong></td>"
        "<td style='text-align: left; width: 30%;'>{name}</td></tr>".format(
            name=self["name"],
        )
    )
    content += (
        "<tr><td style='text-align: left; width: 30%;'><strong>Last Seen: </strong></td>"
        "<td style='text-align: left; width: 30%;'>{last_seen}</td></tr>".format(
            last_seen=self["last_seen"],
        )
    )
    content += "</tbody></table><br><br>"
    content += (
        '<p><strong>More Info: <a target="_blank" href=https://viz.greynoise.io/ip/'
        "{ip}>https://viz.greynoise.io/ip/{ip}</a></strong>&nbsp; </p>".format(
            ip=self["ip"],
        )
    )

    return content


def to_riot_insight(self):
    content = ""
    content += "<table style='100%'><tbody>"
    content += (
        "<tr><td style='text-align: left; width: 30%;'><strong style='font-size: 17px;"
        "color:#1dbf11'><span>Common Business Service</span></strong></td>"
    )
    content += "</tbody></table><br>"
    content += (
        "<p>This IP is from a known business services and can "
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
        "<tr><td style='text-align: left; width: 30%;'><strong>Last Updated: </strong>"
        "</td><td style='text-align: left; width: 30%;'>{last_updated}</td></tr>".format(
            last_updated=self["last_seen"],
        )
    )
    content += "</tbody></table><br><br>"
    content += (
        '<p><strong>More Info: <a target="_blank" href=https://viz.greynoise.io/riot/'
        "{ip}>https://viz.greynoise.io/ip/{ip}</a></strong>&nbsp; </p>".format(
            ip=self["ip"],
        )
    )

    return content


if __name__ == "__main__":
    main()
