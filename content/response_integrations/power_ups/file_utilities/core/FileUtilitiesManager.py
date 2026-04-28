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

import requests
from filelock import FileLock

from .exceptions import EntityFileManagerException, FileUtilitiesHTTPException


class EntityFileManager:
    def __init__(self, filepath, timeout=None):
        """Initiate the manager. This will create a file.lock in the same folder as the filepath.
        :param filepath:
        :param timeout:
        """
        self.filepath = filepath
        self.timeout = timeout

        self.lockpath = self.filepath + ".lock"
        if self.timeout:
            self.lock = FileLock(self.lockpath, timeout=self.timeout)
        else:
            self.lock = FileLock(self.lockpath)
        self.entities = []

    def __enter__(self):
        """Execute with a "with" statement. Acquire the lock,
        and block other processes from using this file (only if it's using py-filelock
        or check the .lock file). Once locked, fetch the rows
        from the file to self.entities to make changes.
        :return:
        """
        self.lock.acquire()
        self.entities = self.read_file()
        return self

    def __exit__(self, typ, value, traceback):
        """End the "with" statement.
        Write the changed to the file and release the lock. All parameters are
        built-ins of python and are not required.
        :param typ: Ignore.
        :param value: Ignore.
        :param traceback: Ignore.
        """
        self.write_file()
        self.lock.release()

    def read_file(self):
        """Helper function to read all entities from the file.
        :return: List with file contents (Entity Identifiers)
        """
        try:
            with open(self.filepath, encoding="utf-8") as f:
                data = f.readlines()
            return [x.strip() for x in data]
        except FileNotFoundError:
            return []

    def write_file(self):
        """Helper function to write the entities list to the file"""
        with open(self.filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(self.entities))

    def add_entity(self, entity):
        """Add elements to self.entities list
        :param entity: Entity identifier
        :return: True
        """
        self.entities.append(entity)
        return True

    def remove_entity(self, entity):
        """Remove elements from self.entities list
        :param entity: Entity identifier
        :return: True
        """
        try:
            self.entities.remove(entity)
            return True
        except KeyError:
            msg = "Entity not found in file"
            raise EntityFileManagerException(msg)


def validate_response(
    response: requests.Response,
    error_msg: str = "An error occurred",
) -> None:
    """Validate response

    Args:
        response (requests.Response): Response to validate
        error_msg (str): Default message to display on error

    Raises:
        FileUtilitiesHTTPException: If there is any error in the response

    """
    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        msg = f"{error_msg}: {error}\n{error.response.content}"
        raise FileUtilitiesHTTPException(msg) from error
