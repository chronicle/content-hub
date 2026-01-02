from __future__ import annotations

import re

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler

from ..core.SpellCheckerManager import SpellCheckerManager

# Consts:
INTEGRATION_NAME = "Spell Checker"
SCRIPT_NAME = "Spelling Check"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    try:
        status = EXECUTION_STATE_COMPLETED
        output_message = "output message :"
        result_value = 0
        failed_entities = []
        successfull_entities = []

        result_json = {}
        spm = SpellCheckerManager()
        input_text = siemplify.parameters.get("Input")
        input_text = re.sub(
            r"[\(\)\r\n,]+",
            " ",
            re.sub(r"[^A-Za-z\s\(\)@]+", "", input_text),
        )
        # raise Exception(json.dumps([x.strip() for x in input_text.split(" ") if x.strip()], indent=4))
        res = spm.spell.unknown(
            [
                x.strip()
                for x in input_text.split(" ")
                if x.strip() and "@" not in x and "http" not in x
            ],
        )

        for item in res:
            result_json[item] = list(spm.spell.candidates(item))
        if result_json:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(result_json),
            )
            result_value = len(result_json)

            # Build table result:
            csv_table = ["Original text ,Recommended corrections"]
            for bad_word, correction_list in result_json.items():
                csv_table.append(
                    "{},{}".format(bad_word, "\u2e41 ".join(correction_list)),
                )
            siemplify.result.add_data_table("Found spelling mistakes", csv_table)

        # print(result_json)
        output_message = f"Found {result_value} mistakes/errors in the text"

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing action {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = -1
        output_message += "\n unknown failure"
        raise

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
