"""Uses DUO's Python SDK: https://github.com/duosecurity/duo_client_python
Uses the DUO Admin API: https://duo.com/docs/adminapi

Obtains user, authentication and device data from DUO MFA on a specific user
and collects last X days of Authentication Logs.
Note: Requires DUO Admin API keys

Created by: jtdepalm@sentara.com
"""

from __future__ import annotations

import json
import time
import traceback

import duo_client
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

INTEGRATION_NAME = "DUO"
SCRIPT_NAME = "DUO Get Authentication Logs"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = True
    status = EXECUTION_STATE_COMPLETED  # used to flag back to siemplify system, the action final status

    def get_duo_user_data(username):
        from time import sleep

        duoApi = siemplify.extract_configuration_param(
            provider_name=INTEGRATION_NAME,
            param_name="API Hostname",
        )
        adminSec = siemplify.extract_configuration_param(
            provider_name=INTEGRATION_NAME,
            param_name="Admin Secret Key",
        )
        adminIntKey = siemplify.extract_configuration_param(
            provider_name=INTEGRATION_NAME,
            param_name="Admin Integration Key",
        )
        try:
            # Using SDK. Setup initial authentication
            admin_api = duo_client.Admin(ikey=adminIntKey, skey=adminSec, host=duoApi)
            # obtain target user's data from DUO. (needed to obtain user_id to request auth logs)
            user_data = admin_api.get_users_by_name(username=username)
            return user_data

        except Exception as e:
            print(e)
            # if error, possibly due to DUO rate limiting, wait and try again
            sleep(60)
            get_duo_user_data(username)

    def get_duo_auth_logs(timestamp_now, timestamp_x_days_ago, user_id):
        from time import sleep

        try:
            user_auth_logs = admin_api.get_authentication_log(
                maxtime=timestamp_now,
                mintime=timestamp_x_days_ago,
                users=user_id,
                api_version=2,
            )
            return user_auth_logs
        except Exception as e:
            print(e)
            sleep(60)
            get_duo_auth_logs(timestamp_now, timestamp_x_days_ago, user_id)

    try:
        # list to contain results from action
        res = []

        duoApi = siemplify.extract_configuration_param(
            provider_name=INTEGRATION_NAME,
            param_name="API Hostname",
        )
        adminSec = siemplify.extract_configuration_param(
            provider_name=INTEGRATION_NAME,
            param_name="Admin Secret Key",
        )
        adminIntKey = siemplify.extract_configuration_param(
            provider_name=INTEGRATION_NAME,
            param_name="Admin Integration Key",
        )

        # ***parameters***
        # target user to obtain logs from
        username = siemplify.extract_action_param("Username", print_value=True)
        # number of days back to obtain logs
        days_back = int(
            siemplify.extract_action_param("Number Days Back", print_value=True),
        )
        # number of successful authentications to needed to trust an authentication source
        auth_threshold = int(
            siemplify.extract_action_param(
                "Authentication Threshold",
                print_value=True,
            ),
        )

        # log to compute number of days back
        x_days_back = (86400 * 1000) * days_back
        timestamp_now = int(time.time() * 1000)
        timestamp_x_days_ago = timestamp_now - x_days_back

        # Using SDK. Setup initial authentication
        admin_api = duo_client.Admin(ikey=adminIntKey, skey=adminSec, host=duoApi)
        # obtain target user's data from DUO. (needed to obtain user_id to request auth logs)
        # user_data = admin_api.get_users_by_name(username=username)
        user_data = get_duo_user_data(username)

        user_id = None
        for data in user_data:
            user_id = data["user_id"]

        if user_id is not None:
            # obtain auth logs for target user
            # user_auth_logs = admin_api.get_authentication_log(maxtime=timestamp_now, mintime=timestamp_x_days_ago, users=user_id, api_version=2)
            user_auth_logs = get_duo_auth_logs(
                timestamp_now,
                timestamp_x_days_ago,
                user_id,
            )
            # dictionaries to hold auth sources to later help with determining known good
            count_access_ip = {}
            count_access_state = {}
            count_access_os = {}
            count_access_app = {}
            count_access_epkey = {}
            count_auth_device = {}
            count_factor = {}
            if user_auth_logs:
                for auth in user_auth_logs["authlogs"]:
                    if auth["result"] == "success":
                        for key, value in auth.items():
                            if "access_device" in key:
                                if "ip" in value:
                                    count_access_ip[value["ip"]] = (
                                        count_access_ip.get(value["ip"], 0) + 1
                                    )
                                if "epkey" in value:
                                    count_access_epkey[value["epkey"]] = (
                                        count_access_epkey.get(value["epkey"], 0) + 1
                                    )
                                if "location" in value:
                                    if "state" in value:
                                        count_access_state[
                                            value["location"]["state"]
                                        ] = (
                                            count_access_state.get(
                                                value["location"]["state"],
                                                0,
                                            )
                                            + 1
                                        )
                                if "os" in value:
                                    count_access_os[value["os"]] = (
                                        count_access_os.get(value["os"], 0) + 1
                                    )
                            if "application" in key:
                                if "name" in value:
                                    count_access_app[value["name"]] = (
                                        count_access_app.get(value["name"], 0) + 1
                                    )
                            if "auth_device" in key:
                                if "name" in value:
                                    count_auth_device[value["name"]] = (
                                        count_access_app.get(value["name"], 0) + 1
                                    )
                            if "factor" in key:
                                if value:
                                    count_factor[value] = count_factor.get(value, 0) + 1
            # add auth source if an auth source matches the auth threshold
            for key, value in list(count_access_ip.items()):
                if value < auth_threshold:
                    count_access_ip.pop(key, None)
            for key, value in list(count_access_state.items()):
                if value < auth_threshold:
                    count_access_state.pop(key, None)
            for key, value in list(count_auth_device.items()):
                if value < auth_threshold:
                    count_auth_device.pop(key, None)
            for key, value in list(count_access_epkey.items()):
                if value < auth_threshold:
                    count_access_epkey.pop(key, None)

            # build final json results
            results = {
                "username": username,
                "user_id": user_id,
                "user_data": user_data,
                "user_auth_logs": user_auth_logs,
                "count_access_epkey": count_access_epkey,
                "count_access_ip": count_access_ip,
                "count_access_state": count_access_state,
                "count_access_os": count_access_os,
                "count_access_app": count_access_app,
                "count_auth_device": count_auth_device,
                "count_factor": count_factor,
            }

            res.append(results)
            siemplify.result.add_result_json(res)

            json_result = json.dumps(res)

            output_message = f"Results: {json_result}"

        else:
            output_message = "No Username provided."

    except Exception:
        result = False
        status = EXECUTION_STATE_FAILED
        # output_message = "Failed. Error is: {}".format(e)
        output_message = f"Failed. Error is: {traceback.format_exc()}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.LOGGER.info(f"Result: {result}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
