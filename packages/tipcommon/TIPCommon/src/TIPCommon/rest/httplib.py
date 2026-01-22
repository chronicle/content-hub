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

import requests
from .auth import generate_jwt_from_sa, generate_jwt_from_credentials


def get_auth_session(
        credentials=None,
        service_account=None,
        audience=None,
        verify_ssl=True
):
    """Creates an Authorized HTTP session to a GCP resource API.

    Args:
        credentials (google.oauth2.credentials.Credentials):
            A `google.oauth2.credentials.Credentials` object
        service_account (str | dict):
            Google cloud project service account with the necessary IAM roles.
        audience (str):
            GCP Scope
        verify_ssl (bool):
            Whether to create session with SSL encryption

    Notes:
        - EITHER `service_account` or `credentials` MUST BE PROVIDED!
        - Either type of credentials object must have the necessary IAM roles configured

    Returns:
        requests.Session: An authorized session object

    Raises:
        ValueError: if credentials and service account are not provided
    """

    if credentials is not None:
        token = generate_jwt_from_credentials(credentials, verify_ssl)
    elif service_account is not None:
        token = generate_jwt_from_sa(
            service_account, audience=audience
        ).decode('utf-8')
    else:
        raise ValueError('credentials or service_account must be provided')

    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }
    session = requests.Session()
    session.headers.update(headers)
    session.verify = verify_ssl
    return session
