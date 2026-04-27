from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction


@output_handler
def main():
    siemplify = SiemplifyAction()

    output_message = "Connection Established"
    result_value = "true"
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
