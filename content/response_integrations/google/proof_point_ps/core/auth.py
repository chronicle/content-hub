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

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from TIPCommon.base.interfaces import Authable
from TIPCommon.base.utils import CreateSession

if TYPE_CHECKING:
    from requests import Session


@dataclasses.dataclass(slots=True)
class SessionAuthenticationParameters:
    """Authentication parameters for session creation."""

    username: str
    password: str
    verify_ssl: bool


class AuthenticatedSession(Authable):
    """Authenticated Session class using Basic Authentication."""

    def authenticate_session(self, params: SessionAuthenticationParameters) -> None:
        """Authenticate the session with the provided credentials.

        Args:
            params: SessionAuthenticationParameters credential details.

        """
        self.session = get_authenticated_session(session_parameters=params)


def get_authenticated_session(
    session_parameters: SessionAuthenticationParameters,
) -> Session:
    """Get authenticated session with provided configuration parameters.

    Args:
        session_parameters: The session parameters containing credentials.

    Returns:
        An authenticated requests.Session object.

    """
    session: Session = CreateSession.create_session()
    _authenticate_session(session, session_parameters=session_parameters)
    return session


def _authenticate_session(
    session: Session,
    session_parameters: SessionAuthenticationParameters,
) -> None:
    """Set SSL verification and basic auth credentials on the session.

    Args:
        session: The requests.Session instance to configure.
        session_parameters: The session parameters containing credentials.

    """
    session.verify = session_parameters.verify_ssl
    session.auth = (session_parameters.username, session_parameters.password)
    session.headers.update(
        {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:50.0) "
            "Gecko/20100101 Firefox/50.0",
        }
    )
