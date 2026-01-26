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

"""
DataStream
==========

Module for handling context management interaction between Siemplify
Integration components and intended context manager.

This module provides a factory class for creating data streams, as well as
abstract base classes for data streams and file streams.

The factory class, ``DataStreamFactory``, can be used to create data streams for
files or databases. The abstract base classes, ``AbstractDataStream`` and
``FileStream``, provide a common interface for all data streams.

The module is importing SiemplifyAction, SiemplifyConnectorExecution and
SiemplifyJob classes from Siemplify SDK so the SDK modules must be either
contained in ``PYTHONPATH`` or in the same environment as the working directory.

This module is wrapped by TIPCommon's ``read_content()`` & ``write_content()``
functions in its core, so usage example will be something like this:

.. code-block:: python

    from TIPCommon import read_content, write_content
    from SiemplifyConnectors import SiemplifyConnectorExecution

    siemplify = SiemplifyConnectorExecution("Test Connector")
    write_content(siemplify, "some data", "file_name", "db_key")
    content = read_content(siemplify, "file_name", "db_key")

"""

import json
import os
import sys

from .utils import platform_supports_db, none_to_default_value, is_empty_string_or_none
from SiemplifyAction import SiemplifyAction
from SiemplifyConnectors import SiemplifyConnectorExecution
from SiemplifyJob import SiemplifyJob


PYTHON_2 = 2
PYTHON_3 = 3


def get_system_python_major_version():
    """Gets the major version of the system Python interpreter.

    The major version is the integer part of the version number,
    e.g., 3 for Python 3.10.

    Returns:
    The major version of the system Python interpreter.
    """
    return sys.version_info.major


if get_system_python_major_version() == PYTHON_3:
    from abc import ABC, abstractmethod

    ##################
    # DATA INTERFACE #
    ##################

    class AbstractDataStream(ABC):
        """An abstract base class for data streams (supporting python 3).

        A data stream is a sequence of data elements that can be read from or
        written to.

        This class defines the following abstract methods:

        * ``validate_existence()``: Checks if the data stream exists.
        * ``read_content()``: Reads the contents of the data stream.
        * ``write_content()``: Writes the contents of the data stream.
        """

        @abstractmethod
        def validate_existence(self, default_value_to_set):
            pass

        @abstractmethod
        def read_content(self, default_value_to_return):
            pass

        @abstractmethod
        def write_content(self, content_to_write, default_value_to_set):
            pass


if get_system_python_major_version() == PYTHON_2:
    from abc import ABCMeta, abstractmethod

    class AbstractDataStream:
        """An abstract base class for data streams (supporting python 2).

        A data stream is a sequence of data elements that can be read from or
        written to.

        This class defines the following abstract methods:

        * ``validate_existence()``: Checks if the data stream exists.
        * ``read_content()``: Reads the contents of the data stream.
        * ``write_content()``: Writes the contents of the data stream.
        """

        __metaclass__ = ABCMeta

        @abstractmethod
        def validate_existence(self, default_value_to_set):
            pass

        @abstractmethod
        def read_content(self, default_value_to_return):
            pass

        @abstractmethod
        def write_content(self, content_to_write, default_value_to_set):
            pass


#################
# FACTORY CLASS #
#################


class DataStreamFactory(object):
    """A factory class for creating data streams.

    Factory class that returns a specific DataStream object that can handle the
    platform's saving methods (Files/database)

    This class defines the following static method:

    * ``get_stream_object()``: Creates a data stream object.
    """

    @staticmethod
    def get_stream_object(file_name, db_key, siemplify, identifier):
        """Get a (connector/action/job) ``DataStream`` object based on platform

        Args:
            file_name (str): The name of the file to read from or write to.
            db_key (str): The key to use to access the database.
            siemplify (``SiemplifyConnectorExecution``|``SiemplifyAction``|``SiemplifyJob``): The Siemplify object to use.
            identifier (str): The identifier of the data stream.

        Returns:
            A ``FileStream`` object if the platform should handle files, or a
            ``DatabaseStream`` object if the platform should handle a database
            for connectors, actions or jobs - depends on the requestor.
        """
        # uses_db = TIPCommon.platform_supports_db(siemplify)
        uses_db = platform_supports_db(siemplify)

        # Connector stream object
        if isinstance(siemplify, SiemplifyConnectorExecution):
            return (
                ConnectorDBStream(db_key, siemplify, identifier)
                if uses_db
                else ConnectorFileStream(file_name, siemplify)
            )
        # Action stream object
        if isinstance(siemplify, SiemplifyAction):
            # TODO: Implement "return ActionDBStream() if is_using_db else ActionFileStream()" once available
            pass

        # Job stream object
        if isinstance(siemplify, SiemplifyJob):
            return (
                JobDBStream(db_key, siemplify, identifier)
                if uses_db
                else JobFileStream(file_name, siemplify)
            )


##################################################################
#           FILES CLASS         ##           FILES CLASS         #
##################################################################


class JobFileStream(AbstractDataStream):
    def __init__(self, file_name, siemplify):
        """JobFileStream class constructor - create a JobFileStream object.

        Args:
            file_name: (str) The name of the file
            siemplify: (SiemplifyJob) An instance of the SDK SiemplifyJob class
        """

        self.siemplify = siemplify
        self.file_path = os.path.join(self.siemplify.run_folder, file_name)

    def validate_existence(self, default_value_to_set):
        """Validate the existence of a ``DataStream`` object.

        If it does not exist, initiate it with default value.

        Args:
            default_value_to_set: (dict/list/str) the default value to be set in case a new file/key is created.

        Note:
            The default value passes through ``json.dumps`` before getting
            written.
        """

        try:
            if not os.path.exists(self.file_path):
                with open(self.file_path, "w+") as map_file:
                    map_file.write(json.dumps(default_value_to_set))
                    self.siemplify.LOGGER.info("File was created at {}".format(self.file_path))

        except Exception as e:
            self.siemplify.LOGGER.error("Unable to create file: {}".format(e))
            self.siemplify.LOGGER.exception(e)

    def read_content(self, default_value_to_return):
        """Read the content of a DataStream object.

        If the object contains no data, does not exist, return a default value

        Args:
            default_value_to_return: (dict|list|str) the default value to be
                set in case a new file/key is created.

        Note:
            If no value is supplied (therefore the default value None
            is used), an internal default value of {} (dict) will be set as
            the new default value.

        Returns:
            (dict) The content inside the DataStream object,
            the content passes through json.loads before returning.
            If the content could not be parsed as a json or if no content was
            found, the default value will return as-is
            (see default_value_to_return parameter doc for further explanation).
        """
        if not os.path.exists(self.file_path):
            self.siemplify.LOGGER.info(
                'file: "{}" does not exist. Returning default value instead: {}'.format(
                    self.file_path, default_value_to_return
                )
            )
            return default_value_to_return

        try:
            with open(self.file_path, "r") as f:
                return json.loads(f.read())

        except Exception as e:
            self.siemplify.LOGGER.error("Unable to read from file: {}".format(e))
            self.siemplify.LOGGER.exception(e)
            return default_value_to_return

    def write_content(self, content_to_write, default_value_to_set):
        """Write content into a DataStream object.

        If the object contains no data, does not exist, return the default.

        Args:
            content_to_write: (dict/list/str) Content that would be written to
                the dedicated data stream.
            default_value_to_set: (dict/list/str) the default value to be set
                in case a new file/key is created.

        Note:
            - The default value passes through json.dumps before getting written.
            - If no value is supplied (default value is None),
                the default identifier will be given using the current siemplify
                object: siemplify.context.connector_info.identifier.
        """
        try:
            if not os.path.exists(os.path.dirname(self.file_path)):
                os.makedirs(os.path.dirname(self.file_path))

            with open(self.file_path, "w") as f:
                try:
                    for chunk in json.JSONEncoder().iterencode(content_to_write):
                        f.write(chunk)

                except Exception as e:
                    self.siemplify.LOGGER.error("Failed writing to file: {}".format(e))
                    self.siemplify.LOGGER.exception(e)
                    # Move seeker to start of the file
                    f.seek(0)
                    # Empty the file's content (the partially written content
                    # that was written before the exception)
                    f.truncate()
                    # Write an empty dict to the file
                    f.write(json.dumps(default_value_to_set))

                return True

        except Exception as err:
            self.siemplify.LOGGER.error("Failed writing to file, ERROR: {}".format(err))
            self.siemplify.LOGGER.exception(err)
            return False


class ConnectorFileStream(AbstractDataStream):
    """A file stream for connecting to a Siemplify connector.

    This class inherits from ``AbstractDataStream`` and provides a way to
    read and write data to a file.

    The following methods are available:

    * ``validate_existence()``: Checks if the file exists.
    * ``read_content()``: Reads the contents of the file.
    * ``write_content()``: Writes the contents of the file.
    """

    def __init__(self, file_name, siemplify):
        """
        ``ConnectorFileStream`` class constructor - create a ``ConnectorFileStream``
         object.

        Args:
            file_name: (str) The name of the file
            siemplify: (obj) An instance of the SDK
                ``SiemplifyConnectorExecution`` class
        """

        self.siemplify = siemplify
        self.file_path = os.path.join(self.siemplify.run_folder, file_name)

    def validate_existence(self, default_value_to_set):
        """Validate the existence of a ``DataStream`` object.

        If it does not exist, initiate it with default value.

        Args:
            default_value_to_set: (dict/list/str) the default value to be set in case a new file/key is created.

        Note:
            The default value passes through ``json.dumps`` before getting
            written.
        """

        try:
            if not os.path.exists(self.file_path):
                with open(self.file_path, "w+") as map_file:
                    map_file.write(json.dumps(default_value_to_set))
                    self.siemplify.LOGGER.info("File was created at {}".format(self.file_path))

        except Exception as e:
            self.siemplify.LOGGER.error("Unable to create file: {}".format(e))
            self.siemplify.LOGGER.exception(e)

    def read_content(self, default_value_to_return):
        """
        Read the content of a ``DataStream`` object.
        If the object contains no data, does not exist, return a default value

        Args:
            default_value_to_return: (dict|list|str) the default value to be set in case a new file/key is created.

        Note:
            If no value is supplied (therefore the default value ``None``
            is used), an internal default value of ``{}`` (dict) will be set as
            the new default value.

        Returns:
            (dict) The content inside the ``DataStream`` object,
            the content passes through ``json.loads`` before returning.
            If the content could not be parsed as a json or if no content was
            found, the default value will return as-is
            (see ``default_value_to_return`` parameter doc for further
            explanation).
        """

        if not os.path.exists(self.file_path):
            self.siemplify.LOGGER.info(
                'file: "{}" does not exist. Returning default value instead: {}'.format(
                    self.file_path, default_value_to_return
                )
            )
            return default_value_to_return

        try:
            with open(self.file_path, "r") as f:
                return json.loads(f.read())

        except Exception as e:
            self.siemplify.LOGGER.error("Unable to read from file: {}".format(e))
            self.siemplify.LOGGER.exception(e)
            return default_value_to_return

    def write_content(self, content_to_write, default_value_to_set):
        """
        Write content into a ``DataStream`` object.
        If the object contains no data, does not exist, return the default.

        Args:
            content_to_write: (dict/list/str) Content that would be written to the dedicated data stream.
            default_value_to_set: (dict/list/str) the default value to be set in case a new file/key is created.

        Note:
            - The default value passes through ``json.dumps`` before getting written.
            - If no value is supplied (default value is ``None``), the default identifier will be given using the current siemplify object: ``siemplify.context.connector_info.identifier``.
        """

        try:
            if not os.path.exists(os.path.dirname(self.file_path)):
                os.makedirs(os.path.dirname(self.file_path))

            with open(self.file_path, "w") as f:
                try:
                    for chunk in json.JSONEncoder().iterencode(content_to_write):
                        f.write(chunk)

                except Exception as e:
                    self.siemplify.LOGGER.error("Failed writing to file: {}".format(e))
                    self.siemplify.LOGGER.exception(e)
                    # Move seeker to start of the file
                    f.seek(0)
                    # Empty the file's content (the partially written content
                    # that was written before the exception)
                    f.truncate()
                    # Write an empty dict to the file
                    f.write(json.dumps(default_value_to_set))

                return True

        except Exception as err:
            self.siemplify.LOGGER.error("Failed writing to file, ERROR: {}".format(err))
            self.siemplify.LOGGER.exception(err)
            return False


##################################################################
#         DATABASE CLASS        ##         DATABASE CLASS        #
##################################################################


class JobDBStream(AbstractDataStream):
    """A DB stream for connecting to a Siemplify job.

    This class inherits from AbstractDataStream and provides a way to read
    and write data to a file.

    The following methods are available:

    * validate_existence(): Checks if the file exists.
    * read_content(): Reads the contents of the file.
    * write_content(): Writes the contents of the file.
    """

    def __init__(self, db_key, siemplify, identifier=None):
        """
        ``ConnectorDBStream class constructor - create a ``ConnectorDBStream``
         object.

        Args:
            db_key: (str) The name of the DB key
            siemplify: (SiemplifyJob) An instance of the SDK SiemplifyJob class
            identifier: (str) The identifier of the connector
        """

        self.siemplify = siemplify
        self.db_key = db_key
        self.identifier = none_to_default_value(
            value_to_check=identifier,
            value_to_return_if_none="{0}_{1}".format(
                self.siemplify.script_name,
                self.siemplify.unique_identifier,
            ),
        )

    def validate_existence(self, default_value_to_set):
        """Validate the existence of a DataStream object.

        If it does not exist, initiate it with default value.

        Args:
            default_value_to_set: (dict/list/str) the default value to be set
                in case a new file/key is created.

        Note:
            The default value passes through json.dumps before getting written
        """
        try:
            existing_data = self.siemplify.get_job_context_property(self.identifier, self.db_key)

            # Check if the db key exists
            if is_empty_string_or_none(existing_data):
                str_data = json.dumps(default_value_to_set, separators=(",", ":"))
                self.siemplify.set_job_context_property(self.identifier, self.db_key, str_data)
                self.siemplify.LOGGER.info("Created key: '{}' in the database".format(self.db_key))

        # If an error happened in the json.dumps methods
        except TypeError as err:
            self.siemplify.LOGGER.error(
                "Failed to parse the default value as JSON. ERROR: {}".format(err)
            )
            self.siemplify.LOGGER.exception(err)
            raise

        # If there is a connection problem with the DB
        except Exception as e:
            self.siemplify.LOGGER.error(
                "Exception was raised from the database. ERROR: {}".format(e)
            )
            self.siemplify.LOGGER.exception(e)
            raise

    def read_content(self, default_value_to_return):
        """
        Read the content of a ``DataStream`` object.
        If the object contains no data, does not exist, return a default value.

        Args:
            default_value_to_return: (dict|list|str) the default value to be
                set in case a new file/key is created.

        Note:
            If no value is supplied (therefore the default value ``None`` is
            used), an internal default value of {} (dict) will be set as
            the new default value.

        Returns:
            (dict) The content inside the ``DataStream`` object,
            the content passes through ``json.loads`` before returning.
            If the content could not be parsed as a json or if no content was
            found, the default value will return as-is.
            (see "default_value_to_return" parameter doc for further
            explanation)
        """
        try:
            str_data = self.siemplify.get_job_context_property(self.identifier, self.db_key)

            # Check if the db key exists
            if is_empty_string_or_none(str_data):
                self.siemplify.LOGGER.info(
                    'Key: "{}" does not exist in the database. '
                    "Returning default value instead:"
                    " {}".format(self.db_key, default_value_to_return)
                )
                return default_value_to_return

            data = json.loads(str_data)
            return data

        # If an error happened in the json.loads methods
        except TypeError as err:
            self.siemplify.LOGGER.error(
                "Failed to parse data as JSON. Returning default value "
                'instead: "{0}". \nERROR: {1}'.format(default_value_to_return, err)
            )
            self.siemplify.LOGGER.exception(err)
            return default_value_to_return

        # If there is a connection problem with the DB
        except Exception as error:
            self.siemplify.LOGGER.error(
                "Exception was raised from the database.  ERROR: {}.".format(error)
            )
            self.siemplify.LOGGER.exception(error)
            raise

    def write_content(self, content_to_write, default_value_to_set):
        """Write content into a DataStream object.

        If the object contains no data, does not exist, return the default.

        Args:
            content_to_write: (dict/list/str) Content that would be written to
                the dedicated data stream.
            default_value_to_set: (dict/list/str) the default value to be set
                in case a new file/key is created.

        Note:
            Both default_value_to_set and content_to_write passes
            through json.dumps before getting written.
            If no value is supplied (therefore the default value None is
            used), an internal default value of {} (dict) will be set as
            the new default value.
        """
        try:
            str_data = json.dumps(content_to_write, separators=(",", ":"))
            self.siemplify.set_job_context_property(self.identifier, self.db_key, str_data)

        # If an error happened in the json.dumps methods
        except TypeError as err:
            self.siemplify.LOGGER.error(
                "Failed parsing JSON to string. Writing default value instead: "
                '"{}". \nERROR: {}'.format(default_value_to_set, err)
            )
            self.siemplify.LOGGER.exception(err)
            self.siemplify.set_job_context_property(
                self.identifier,
                self.db_key,
                json.dumps(default_value_to_set, separators=(",", ":")),
            )
        # If there is a connection problem with the DB
        except Exception as err:
            self.siemplify.LOGGER.error(
                "Exception was raised from the database.  ERROR: {}".format(err)
            )
            self.siemplify.LOGGER.exception(err)
            raise


class ConnectorDBStream(AbstractDataStream):
    """A DB stream for connecting to a Siemplify connector.

    This class inherits from ``AbstractDataStream`` and provides a way to read
    and write data to a file.

    The following methods are available:

    * ``validate_existence()``: Checks if the file exists.
    * ``read_content()``: Reads the contents of the file.
    * ``write_content()``: Writes the contents of the file.
    """

    def __init__(self, db_key, siemplify, identifier):
        """
        ``ConnectorDBStream class constructor - create a ``ConnectorDBStream``
         object.

        Args:
            db_key: (str) The name of the DB key
            siemplify: (obj) An instance of the SDK
                ``SiemplifyConnectorExecution`` class
            identifier: (str) The identifier of the connector
        """

        self.siemplify = siemplify
        self.db_key = db_key
        self.identifier = none_to_default_value(
            value_to_check=identifier,
            value_to_return_if_none=self.siemplify.context.connector_info.identifier,
        )

    def validate_existence(self, default_value_to_set):
        """
        Validate the existence of a ``DataStream`` object.
        If it does not exist, initiate it with default value.

        Args:
            default_value_to_set: (dict/list/str) the default value to be set in case a new file/key is created.

        Note:
            The default value passes through ``json.dumps``
            before getting written
        """
        try:
            existing_data = self.siemplify.get_connector_context_property(
                self.identifier, self.db_key
            )

            # Check if the db key exists
            if is_empty_string_or_none(existing_data):
                str_data = json.dumps(default_value_to_set, separators=(",", ":"))
                self.siemplify.set_connector_context_property(
                    self.identifier, self.db_key, str_data
                )
                self.siemplify.LOGGER.info("Created key: '{}' in the database".format(self.db_key))

        # If an error happened in the json.dumps methods
        except TypeError as err:
            self.siemplify.LOGGER.error(
                "Failed to parse the default value as JSON. ERROR: {}".format(err)
            )
            self.siemplify.LOGGER.exception(err)
            raise

        # If there is a connection problem with the DB
        except Exception as e:
            self.siemplify.LOGGER.error(
                "Exception was raised from the database. ERROR: {}".format(e)
            )
            self.siemplify.LOGGER.exception(e)
            raise

    def read_content(self, default_value_to_return):
        """
        Read the content of a ``DataStream`` object.
        If the object contains no data, does not exist, return a default value.

        Args:
            default_value_to_return: (dict|list|str) the default value to be set in case a new file/key is created.

        Note:
            If no value is supplied (therefore the default value ``None`` is
            used), an internal default value of {} (dict) will be set as
            the new default value.

        Returns:
            (dict) The content inside the ``DataStream`` object,
            the content passes through ``json.loads`` before returning.
            If the content could not be parsed as a json or if no content was
            found, the default value will return as-is.
            (see "default_value_to_return" parameter doc for further explanation)
        """

        try:
            str_data = self.siemplify.get_connector_context_property(self.identifier, self.db_key)

            # Check if the db key exists
            if is_empty_string_or_none(str_data):
                self.siemplify.LOGGER.info(
                    'Key: "{}" does not exist in the database. '
                    "Returning default value instead:"
                    " {}".format(self.db_key, default_value_to_return)
                )
                return default_value_to_return

            data = json.loads(str_data)
            return data

        # If an error happened in the json.loads methods
        except TypeError as err:
            self.siemplify.LOGGER.error(
                "Failed to parse data as JSON. Returning default value "
                'instead: "{0}". \nERROR: {1}'.format(default_value_to_return, err)
            )
            self.siemplify.LOGGER.exception(err)
            return default_value_to_return

        # If there is a connection problem with the DB
        except Exception as error:
            self.siemplify.LOGGER.error(
                "Exception was raised from the database.  ERROR: {}.".format(error)
            )
            self.siemplify.LOGGER.exception(error)
            raise

    def write_content(self, content_to_write, default_value_to_set):
        """
        Write content into a ``DataStream`` object.
        If the object contains no data, does not exist, return the default.

        Args:
            content_to_write: (dict/list/str) Content that would be written to the dedicated data stream.
            default_value_to_set: (dict/list/str) the default value to be set in case a new file/key is created.

        Note:
            Both ``default_value_to_set`` and ``content_to_write`` passes
            through ``json.dumps`` before getting written.
            If no value is supplied (therefore the default value ``None`` is
            used), an internal default value of ``{}`` (dict) will be set as
            the new default value.
        """
        # separators=(',', ':')
        try:
            str_data = json.dumps(content_to_write, separators=(",", ":"))
            self.siemplify.set_connector_context_property(self.identifier, self.db_key, str_data)

        # If an error happened in the json.dumps methods
        except TypeError as err:
            self.siemplify.LOGGER.error(
                "Failed parsing JSON to string. Writing default value instead: "
                '"{}". \nERROR: {}'.format(default_value_to_set, err)
            )
            self.siemplify.LOGGER.exception(err)
            self.siemplify.set_connector_context_property(
                self.identifier,
                self.db_key,
                json.dumps(default_value_to_set, separators=(",", ":")),
            )
        # If there is a connection problem with the DB
        except Exception as err:
            self.siemplify.LOGGER.error(
                "Exception was raised from the database.  ERROR: {}".format(err)
            )
            self.siemplify.LOGGER.exception(err)
            raise


def validate_existence(file_name, db_key, default_value_to_set, siemplify, identifier=None):
    """
    Validates the existence of a ``DataStream`` object.
    If it does not exist, initiate it with default value.

    Args:
        siemplify: (obj) An instance of the SDK ``SiemplifyConnectorExecution`` class.
        file_name: (str) the name of the file to be validated (in case the platform uses files).
        db_key: (str) the name of the key to be validated (in case the platform uses database).
        default_value_to_set: (dict/list/str) the default value to be set in case a new file/key is created.
        identifier: The connector's identifier attribute.

    Note:
        - The default value passes through ``json.dumps`` before getting written.
        - If no value is supplied (default value is ``None``), the default identifier will be given using the current siemplify object: ``siemplify.context.connector_info.identifier``.

    Returns:
        None
    """

    data = DataStreamFactory.get_stream_object(file_name, db_key, siemplify, identifier)
    data.validate_existence(default_value_to_set)
