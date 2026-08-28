# Copyright 2026 Google LLC
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

import pathlib
import os


def create_test_attachment(path: str, attachment_name: str) -> str:
    """
    Create a test attachment

    Returns:
        str: path to created attachment
    """
    attachment_content = b"This is a test content"

    if not os.path.exists(path):
        os.makedirs(path)

    local_path = os.path.join(path, attachment_name)

    with open(local_path, "wb") as f:
        f.write(attachment_content)

    return local_path


def delete_test_attachments(path: str):
    """
    Delete test attachment

    Args:
        path (str): CSV of path to test attachments
    """
    for file in path.split(","):
        try:
            os.remove(file)
        except FileNotFoundError:
            # File not found
            pass
