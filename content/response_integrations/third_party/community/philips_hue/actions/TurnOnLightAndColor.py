from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.PhilipsManager import PhilipsManager

# Consts:
INTEGRATION_NAME = "PhilipsHUE"
SCRIPT_NAME = "Turn On Light and Color"
COLORS = {
    "Red": 65522,
    "Orange": 4080,
    "Yellow": 8000,
    "Green": 17500,
    "Blue": 43431,
    "Purple": 49311,
    "Pink": 56000,
}
EFFECTS = {"None": "none", "Flicker-Once": "select", "Flicker-Loop": "lselect"}


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # Extract Integration params:
    bridge_ip = siemplify.extract_configuration_param(INTEGRATION_NAME, "Bridge IP")
    username = siemplify.extract_configuration_param(
        INTEGRATION_NAME,
        "Authorized Username",
    )

    # Init Action params:
    light_id = siemplify.extract_action_param(param_name="Light ID")
    color_name = siemplify.extract_action_param(param_name="Color")
    alert_effect_chosen = siemplify.extract_action_param(param_name="Alert effect")
    color_code = COLORS[color_name]
    alert_effect = EFFECTS[alert_effect_chosen]

    # Instanciate manager for methods:
    philipsManager = PhilipsManager(bridge_ip, username)

    # Instanciate result json:
    res_json = {}
    res_json["light_id"] = light_id

    # Init action reault values:
    status = EXECUTION_STATE_FAILED
    output_message = f"Failed to turn the light <{light_id}> on with hue color <{color_code}> and <{alert_effect_chosen}> effect. "
    result_value = False

    try:
        # check ID:
        id_available = philipsManager.search_light_id(light_id)
        if id_available:
            # turn light on:
            res_json["info"] = philipsManager.adjust_light(
                light_id,
                True,
                color_code,
                alert_effect,
            )
            if not res_json.get("info").get("light reachability"):
                output_message += f"Light <{light_id}> is unreachable."
            else:
                status = EXECUTION_STATE_COMPLETED
                output_message = f"Successfully turned the light <{light_id}> on with color <{color_name}> and <{alert_effect_chosen}> effect."
                result_value = True
        else:
            status = EXECUTION_STATE_FAILED
            output_message = f"Light with <{light_id}> does not exist under the bridge <{bridge_ip}>."
            result_value = False

    except Exception as e:
        siemplify.LOGGER.error(e)
        output_message += "Error: " + str(e)

    finally:
        siemplify.LOGGER.info(
            f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
        )
        siemplify.result.add_result_json(res_json)
        siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
