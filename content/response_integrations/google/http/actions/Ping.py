from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction


@output_handler
def main():
    siemplify = SiemplifyAction()
    output_message = "Connected Successfully"
    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
