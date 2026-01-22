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



from .consts import (
    IDS_DB_KEY,
    IDS_FILE_NAME,
    NUM_OF_HOURS_IN_3_DAYS,
    STORED_IDS_LIMIT
)
from .DataStream import DataStreamFactory
from .filters import filter_old_ids_by_timestamp
from .types import ChronicleSOAR
from .utils import (
    none_to_default_value,
    cast_keys_to_int
)


def read_content(
    siemplify,
    file_name,
    db_key,
    default_value_to_return=None,
    identifier=None
):
    """
    Read the content of a `ConnectorStream` object.
    If the object contains no data, does not exist, return a default value

    Args:
        siemplify: (obj) An instance of the SDK `SiemplifyConnectorExecution` class.
        file_name: (str) The name of the file to be validated (in case the platform uses files)
        db_key: (str) The name of the key to be validated (in case the platform uses database)
        default_value_to_return: (dict/list/str) The default value to be set in case a new file/key is created.
                                    If no value is supplied, an internal default value of {} (dict) will be set as
                                    the new default value.
        identifier: (str) The connector's identifier attribute.

    Returns:
        (dict) The content inside the `DataStream` object, the content passes through `json.loads` before returning.
    """

    data = DataStreamFactory.get_stream_object(
        file_name,
        db_key,
        siemplify,
        identifier
    )

    default_value_to_return = none_to_default_value(default_value_to_return, {})

    return data.read_content(default_value_to_return)


def read_ids(
    siemplify,
    default_value_to_return=None,
    identifier=None,
    ids_file_name=IDS_FILE_NAME,
    db_key=IDS_DB_KEY
):
    """
    Read IDs from a `ConnectorStream` object.
    If the object contains no data, does not exist, return a default value

    Args:
        siemplify: (obj) An instance of the SDK `SiemplifyConnectorExecution` class.
        default_value_to_return: (dict/list/str) The default value to be set in case a new file/key is created.
                                    If no value is supplied, an internal default value of [] (list) will be set as
                                    the new default value.
        identifier: (str) The connector's identifier attribute.
        ids_file_name: (str) The file name where IDs should be saved when `FileStream` object had been created.
        db_key: (str) The key name where IDs should be saved when `FileStream` object had been created.

    Returns:
        (list) List of IDs inside the `DataStream` object, the content passes through `json.loads` before returning.
    """

    default_value_to_return = none_to_default_value(default_value_to_return, [])

    return read_content(
        siemplify,
        ids_file_name,
        db_key,
        default_value_to_return,
        identifier
    )


def read_ids_by_timestamp(
    siemplify,
    offset_in_hours=NUM_OF_HOURS_IN_3_DAYS,
    default_value_to_return=None,
    convert_to_milliseconds=False,
    cast_keys_to_integers=False,
    offset_is_in_days=False,
    identifier=None,
    ids_file_name=IDS_FILE_NAME,
    db_key=IDS_DB_KEY
):
    """
    Read IDs from a `ConnectorStream` object.
    If the object contains no data, does not exist, return a default value

    Args:
        siemplify: (obj) An instance of the SDK `SiemplifyConnectorExecution` class.
        offset_in_hours: (int) The IDs time limit (offset value) in hours.
        convert_to_milliseconds: (bool) Transform each ID's timestamp (unix) from seconds to milliseconds.
        cast_keys_to_integers: (bool) Cast the keys to integers.
        default_value_to_return: (dict/list/str) The default value to be set in case a new file/key is created.
        offset_is_in_days: (bool) If the offset supplied to this method is in days, please mark this as True for
                                    converting the offset days into hours.
        identifier: (str) The connector's identifier attribute.
        ids_file_name: (str) The file name where IDs should be saved when `FileStream` object had been created.
        db_key: (str) The key name where IDs should be saved when `FileStream` object had been created.

    Returns:
        (list) List of IDs inside the `DataStream` object, the content passes through `json.loads` before returning.
    """

    existing_ids = read_content(
        siemplify,
        ids_file_name,
        db_key,
        default_value_to_return,
        identifier
    )

    try:
        filtered_ids = filter_old_ids_by_timestamp(
            ids=existing_ids,
            offset_in_hours=offset_in_hours,
            convert_to_milliseconds=convert_to_milliseconds,
            offset_is_in_days=offset_is_in_days
        )
        if cast_keys_to_integers:
            return cast_keys_to_int(filtered_ids)

        return filtered_ids

    except Exception as e:
        siemplify.LOGGER.error('Unable to read ids file: {}'.format(e))
        siemplify.LOGGER.exception(e)

        default_value_to_return = none_to_default_value(
            default_value_to_return,
            {}
        )
        return default_value_to_return


def read_and_repair_existing_ids(
    siemplify,
    default_value_to_return=None,
    identifier=None,
    ids_file_name=IDS_FILE_NAME,
    db_key=IDS_DB_KEY
):
    # type: (ChronicleSOAR, dict, str, str, str) -> list
    """Read existing alert ids and convert them to list, if it is a dict.
    This is needed to avoid regressions.

    Args:
        siemplify: (SiemplifyConnectorExecution) An instance of the SDK
        `SiemplifyConnectorExecution` class.
        default_value_to_return: (dict/list/str) The default value to be set in
            case a new file/key is created.
            If no value is supplied, an internal default value of [] (list) will
            be set as the new default value.
        identifier: (str) The connector's identifier attribute.
        ids_file_name: (str) The file name where IDs should be saved when
            `FileStream` object had been created.
        db_key: (str) The key name where IDs should be saved when `FileStream`
            object had been created.

    Returns:
        list: List of IDs inside the `DataStream` object.
    """
    existing_ids_data = read_ids(
        siemplify=siemplify,
        default_value_to_return=default_value_to_return,
        identifier=identifier,
        ids_file_name=ids_file_name,
        db_key=db_key
        )

    if isinstance(existing_ids_data, dict):
        return list(existing_ids_data.keys())

    return existing_ids_data


########################################################################################
#              WRITE  METHODS              ##              WRITE  METHODS              #
########################################################################################

def write_content(
    siemplify,
    content_to_write,
    file_name,
    db_key,
    default_value_to_set=None,
    identifier=None
):
    """Writes content into a `ConnectorStream` object.

    Args:
        siemplify: (obj) An instance of the SDK `SiemplifyConnectorExecution` class.
        content_to_write: (dict/list/str) The content to be written to the dedicated data stream.
        file_name: (str) The name of the file to be written to.
        db_key: (str) The name of the key to be written to.
        default_value_to_set: (dict/list/str) The default value to be set in case a new file/key is created.
        identifier: (str) The connector's identifier attribute.

    Returns:
        None
    """
    data = DataStreamFactory.get_stream_object(
        file_name,
        db_key,
        siemplify,
        identifier
    )

    default_value_to_set = none_to_default_value(default_value_to_set, {})

    data.write_content(content_to_write, default_value_to_set)


def write_ids(
    siemplify,
    ids,
    default_value_to_set=None,
    stored_ids_limit=STORED_IDS_LIMIT,
    identifier=None,
    ids_file_name=IDS_FILE_NAME,
    db_key=IDS_DB_KEY
):
    """Writes the last 1,000 IDs into a `ConnectorStream` object.

    Args:
        siemplify: (obj) An instance of the SDK `SiemplifyConnectorExecution` class.
        ids: (list/str) The IDs to be written to the dedicated data stream.
        default_value_to_set: (dict/list/str) The default value to be set in case a new file/key is created.
        stored_ids_limit: (int) The number of recent IDs from the existing ids which will be written.
        identifier: (str) The connector's identifier attribute.
        ids_file_name: (str) The file name where IDs should be saved when `FileStream` object had been created.
        db_key: (str) The key name where IDs should be saved when `FileStream` object had been created.

    Returns:
        None
    """

    default_value_to_set = none_to_default_value(default_value_to_set, [])

    ids = ids[-stored_ids_limit:]
    write_content(
        siemplify,
        ids,
        ids_file_name,
        db_key,
        default_value_to_set,
        identifier
    )


def write_ids_with_timestamp(
    siemplify,
    ids,
    default_value_to_set=None,
    identifier=None,
    ids_file_name=IDS_FILE_NAME,
    db_key=IDS_DB_KEY
):
    """Writes IDs into a `ConnectorStream` object with a timestamp.

    Args:
        siemplify: (obj) An instance of the SDK `SiemplifyConnectorExecution` class.
        ids: (dict/list/str) The IDs to be written to the dedicated data stream.
        default_value_to_set: (dict/list/str) The default value to be set in case a new file/key is created.
        identifier: (str) The connector's identifier attribute.
        ids_file_name: (str) The file name where IDs should be saved when `FileStream` object had been created.
        db_key: (str) The key name where IDs should be saved when `FileStream` object had been created.

    Returns:
        None
    """

    default_value_to_set = none_to_default_value(default_value_to_set, {})

    write_content(
        siemplify,
        ids,
        ids_file_name,
        db_key,
        default_value_to_set,
        identifier
    )
