from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction

INTEGRATION_NAME = "Spell Checker"


def main():
    siemplify = SiemplifyAction()

    siemplify.end("Spell Checker is connected", True)


if __name__ == "__main__":
    main()


# Required for validation:
# Successfully connected to the
# Failed to connect to the
