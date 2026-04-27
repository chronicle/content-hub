from __future__ import annotations
import sys

from EnvironmentCommon import GetEnvironmentCommonFactory
from ..core.Rapid7Manager import Rapid7Manager
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon import (
    read_ids,
    is_approaching_timeout,
    pass_whitelist_filter,
    convert_list_to_comma_string,
    is_overflowed,
    extract_connector_param,
)
from ..core.UtilsManager import pass_severity_filter, write_ids
from ..core.constants import (
    CONNECTOR_NAME,
    SEVERITIES,
    POSSIBLE_GROUPINGS,
    DEFAULT_ASSET_LIMIT,
    HOST_GROUPING,
    NONE_GROUPING,
    STORED_IDS_LIMIT,
)

connector_starting_time = unix_now()


@output_handler
def main(is_test_run):
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = CONNECTOR_NAME
    processed_alerts = []

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("------------------- Main - Param Init -------------------")

    api_root = extract_connector_param(
        siemplify, param_name="API Root", is_mandatory=True, print_value=True
    )
    username = extract_connector_param(
        siemplify, param_name="Username", is_mandatory=True, print_value=True
    )
    password = extract_connector_param(
        siemplify, param_name="Password", is_mandatory=True
    )
    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    environment_field_name = extract_connector_param(
        siemplify, param_name="Environment Field Name", print_value=True
    )
    environment_regex_pattern = extract_connector_param(
        siemplify, param_name="Environment Regex Pattern", print_value=True
    )

    script_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        is_mandatory=True,
        input_type=int,
        print_value=True,
    )
    lowest_severity_to_fetch = extract_connector_param(
        siemplify, param_name="Lowest Severity To Fetch", print_value=True
    )
    fetch_limit = extract_connector_param(
        siemplify,
        param_name="Max Assets To Process",
        input_type=int,
        default_value=DEFAULT_ASSET_LIMIT,
        print_value=True,
    )
    grouping_mechanism = extract_connector_param(
        siemplify, param_name="Grouping Mechanism", is_mandatory=True, print_value=True
    )
    whitelist_as_a_blacklist = extract_connector_param(
        siemplify,
        "Use whitelist as a blacklist",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    device_product_field = extract_connector_param(
        siemplify, "DeviceProductField", is_mandatory=True
    )
    grouping_mechanism = grouping_mechanism.title()

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        if fetch_limit < 1:
            siemplify.LOGGER.info(
                "Max Assets To Process must be greater than zero. The default value {} "
                "will be used".format(DEFAULT_ASSET_LIMIT)
            )
            fetch_limit = DEFAULT_ASSET_LIMIT

        if (
            lowest_severity_to_fetch
            and lowest_severity_to_fetch.lower() not in SEVERITIES
        ):
            raise Exception(
                "Invalid value given for Lowest Severity To Fetch parameter. Possible values are: "
                "{}.".format(
                    convert_list_to_comma_string(
                        [severity.title() for severity in SEVERITIES]
                    )
                )
            )

        if grouping_mechanism not in POSSIBLE_GROUPINGS:
            siemplify.LOGGER.error(
                f"Invalid value given for Grouping Mechanism. {NONE_GROUPING} will be used"
            )
            grouping_mechanism = NONE_GROUPING

        # Read already existing alerts ids
        assets_list = read_ids(siemplify)
        siemplify.LOGGER.info("Successfully loaded existing assets from ids file")

        manager = Rapid7Manager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        filtered_assets, assets_list = manager.get_assets(
            assets_list=assets_list, limit=fetch_limit
        )

        siemplify.LOGGER.info(f"Fetched {len(filtered_assets)} assets")
        fetched_vulnerabilities = []

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 asset will be processed.")
            filtered_assets = filtered_assets[:1]

        for asset in filtered_assets:
            try:
                if is_approaching_timeout(connector_starting_time, script_timeout):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                siemplify.LOGGER.info(f"Started processing asset {asset.id}")
                asset_json = next(
                    (
                        item
                        for item in assets_list
                        if item.get("asset_id", None) == asset.id
                    ),
                    {},
                )

                environment_common = (
                    GetEnvironmentCommonFactory.create_environment_manager(
                        siemplify, environment_field_name, environment_regex_pattern
                    )
                )

                for alert in manager.get_asset_vulnerabilities(
                    asset_id=asset.id, existing_ids=asset_json["vulnerabilities"]
                ):
                    siemplify.LOGGER.info(
                        f"Started processing vulnerability {alert.id}"
                    )

                    existing_alert = next(
                        (
                            item
                            for item in fetched_vulnerabilities
                            if item.id == alert.id
                        ),
                        None,
                    )
                    if existing_alert:
                        alert = existing_alert
                    else:
                        alert.details = manager.get_vulnerability_details(
                            vulnerability_id=alert.id
                        )
                        fetched_vulnerabilities.append(alert)

                    if not pass_filters(
                        siemplify,
                        whitelist_as_a_blacklist,
                        alert.details,
                        "title",
                        lowest_severity_to_fetch,
                    ):
                        continue

                    # Update existing alerts
                    asset_json["vulnerabilities"].append(alert.id)
                    asset.vulnerabilities.append(alert)

                    if grouping_mechanism == NONE_GROUPING:
                        alert_info = alert.get_alert_info(
                            alert_info=AlertInfo(),
                            environment_common=environment_common,
                            device_product_field=device_product_field,
                        )

                        if is_overflowed(siemplify, alert_info, is_test_run):
                            siemplify.LOGGER.info(
                                "{alert_name}-{alert_identifier}-{environment}-{product} found as overflow alert. "
                                "Skipping...".format(
                                    alert_name=str(alert_info.rule_generator),
                                    alert_identifier=str(alert_info.ticket_id),
                                    environment=str(alert_info.environment),
                                    product=str(alert_info.device_product),
                                )
                            )
                            # If is overflowed we should skip
                            continue

                        siemplify.LOGGER.info(f"Alert {alert.id} was created.")
                        processed_alerts.append(alert_info)

                    siemplify.LOGGER.info(
                        f"Finished processing vulnerability {alert.id}"
                    )

                if grouping_mechanism == HOST_GROUPING and asset.vulnerabilities:
                    alert_info = asset.get_alert_info(
                        alert_info=AlertInfo(),
                        environment_common=environment_common,
                        device_product_field=device_product_field,
                        execution_time=connector_starting_time,
                    )

                    if is_overflowed(siemplify, alert_info, is_test_run):
                        siemplify.LOGGER.info(
                            "{alert_name}-{alert_identifier}-{environment}-{product} found as overflow alert. "
                            "Skipping...".format(
                                alert_name=str(alert_info.rule_generator),
                                alert_identifier=str(alert_info.ticket_id),
                                environment=str(alert_info.environment),
                                product=str(alert_info.device_product),
                            )
                        )
                        # If is overflowed we should skip
                        continue

                    siemplify.LOGGER.info(f"Alert {asset.id} was created.")
                    processed_alerts.append(alert_info)

                asset_json["vulnerabilities"] = asset_json["vulnerabilities"][
                    -STORED_IDS_LIMIT:
                ]
                asset_json["processed"] = True

            except Exception as e:
                siemplify.LOGGER.error(f"Failed to process asset {asset.id}")
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

            siemplify.LOGGER.info(f"Finished processing asset {asset.id}")

        if not is_test_run:
            siemplify.LOGGER.info("Saving existing ids.")
            write_ids(siemplify, assets_list)

    except Exception as e:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {e}")
        siemplify.LOGGER.exception(e)

        if is_test_run:
            raise

    siemplify.LOGGER.info(f"Created total of {len(processed_alerts)} cases")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_alerts)


def pass_filters(
    siemplify, whitelist_as_a_blacklist, alert, model_key, lowest_risk_to_fetch
):
    # All alert filters should be checked here
    if not pass_whitelist_filter(siemplify, whitelist_as_a_blacklist, alert, model_key):
        return False

    if not pass_severity_filter(siemplify, alert, lowest_risk_to_fetch):
        return False

    return True


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
