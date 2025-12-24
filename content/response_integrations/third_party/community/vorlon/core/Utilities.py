from __future__ import annotations

from datetime import datetime


def validate_response(response, error_msg="Error found"):
    try:
        response.raise_for_status()
    except Exception:
        try:
            response.json()
        except Exception as e:
            raise Exception(f"Malformed response. Error is {e}")

        response_json = response.json()
        errors = response_json.get("error_description")
        if errors:
            raise Exception(
                f"Error in validating the response. Detailed error - {errors}",
            )


def remove_spaces(param=None):
    try:
        return ",".join([word.strip() for word in param.split(",")])
    except Exception as e:
        raise Exception(f"An error occurred: {e}")


def validate_and_convert_to_epoch(date_str):
    format_str = "%Y-%m-%dT%H:%M:%S"
    try:
        dt = datetime.strptime(date_str, format_str)
        epoch_time = int(dt.timestamp())
        return epoch_time
    except ValueError:
        raise Exception(
            "The input datetime is not in a valid format. Please provide the input in the format YYYY-MM-DDTHH:MM:SS",
        )
