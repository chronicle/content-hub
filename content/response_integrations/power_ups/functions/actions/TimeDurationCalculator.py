# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from datetime import UTC, datetime

import pytz
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


def getDuration(then, now=datetime.now(UTC), interval="default"):
    # Returns a duration as specified by variable interval
    # Functions, except totalDuration, returns [quotient, remainder]

    duration = now - then  # For build-in functions
    duration_in_s = duration.total_seconds()

    def years():
        return divmod(duration_in_s, 31536000)  # Seconds in a year=31536000.

    def days(seconds=None):
        return divmod(
            seconds if seconds is not None else duration_in_s,
            86400,
        )  # Seconds in a day = 86400

    def hours(seconds=None):
        return divmod(
            seconds if seconds is not None else duration_in_s,
            3600,
        )  # Seconds in an hour = 3600

    def minutes(seconds=None):
        return divmod(
            seconds if seconds is not None else duration_in_s,
            60,
        )  # Seconds in a minute = 60

    def seconds(seconds=None):
        if seconds is not None:
            return divmod(seconds, 1)
        return duration_in_s

    def totalDuration():
        y = years()
        d = days(y[1])  # Use remainder to calculate next variable
        h = hours(d[1])
        m = minutes(h[1])
        s = seconds(m[1])

        return f"Time between dates: {int(y[0])} years, {int(d[0])} days, {int(h[0])} hours, {int(m[0])} minutes and {int(s[0])} seconds"

    return {
        "years": int(years()[0]),
        "days": int(days()[0]),
        "hours": int(hours()[0]),
        "minutes": int(minutes()[0]),
        "seconds": int(seconds()),
        "default": totalDuration(),
    }[interval]


def tz_aware(dt):
    # date TZ awareness check function
    return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None


@output_handler
def main():
    siemplify = SiemplifyAction()
    status = EXECUTION_STATE_COMPLETED  # used to flag back to siemplify system, the action final status
    output_message = (
        "output message :"  # human readable message, showed in UI as the action result
    )
    result_value = (
        None  # Set a simple result value, used for playbook if\else and placeholders.
    )
    json_results = {}
    input_datetime1 = siemplify.extract_action_param(
        "Input DateTime 1",
        print_value=True,
    )
    input_datetime1_format = siemplify.extract_action_param(
        "Input DateTime 1 Format",
        print_value=True,
    )
    input_datetime2 = siemplify.extract_action_param(
        "Input DateTime 2",
        print_value=True,
    )
    input_datetime2_format = siemplify.extract_action_param(
        "Input DateTime 2 Format",
        print_value=True,
    )

    if input_datetime1 == "now":
        input_dt1 = datetime.now(UTC)
        output_message += f"Date Time 1 using now, which is {input_dt1}\n"
    else:
        input_dt1 = datetime.strptime(input_datetime1, input_datetime1_format)
        output_message += f"Date Time 1 is {input_dt1}\n"
        if not tz_aware(input_dt1):
            output_message += "Date Time 1 not localized!, and will be corrected!\n"
            siemplify.LOGGER.info("Date Time 1 not localized!")
            input_dt1 = pytz.utc.localize(input_dt1)

    if input_datetime2 == "now":
        input_dt2 = datetime.now(UTC)
        output_message += f"Date Time 2 using now, which is {input_dt2}\n"
    else:
        input_dt2 = datetime.strptime(input_datetime2, input_datetime2_format)
        output_message += f"Date Time 2 is {input_dt2}\n"
        if not tz_aware(input_dt2):
            output_message += "Date Time 2 not localized!, and will be corrected!\n"
            siemplify.LOGGER.info("Date Time 2 not localized!")
            input_dt2 = pytz.utc.localize(input_dt2)

    siemplify.LOGGER.info(f"Date Time 1 is {input_dt1}\n")
    siemplify.LOGGER.info(f"Date Time 2 is {input_dt2}\n")

    duration = getDuration(input_dt1, input_dt2)
    output_message += f"Duration is {duration!s}\n"

    json_results["years"] = getDuration(input_dt1, input_dt2, "years")
    json_results["days"] = getDuration(input_dt1, input_dt2, "days")
    json_results["hours"] = getDuration(input_dt1, input_dt2, "hours")
    json_results["minutes"] = getDuration(input_dt1, input_dt2, "minutes")
    json_results["seconds"] = getDuration(input_dt1, input_dt2, "seconds")
    json_results["duration"] = duration
    siemplify.result.add_result_json(json_results)
    output_message = f"The duration between {input_datetime1} and {input_datetime2} is {json_results['duration']}"
    output_message += "calculation complete!\n.\n"
    result_value = json_results["seconds"]
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
