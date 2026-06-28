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
import re
import json
import time
import uuid
from datetime import datetime
from typing import List, Optional

import jwt
import requests
from requests import Response, Session

from TIPCommon.base.utils import CreateSession
from TIPCommon.types import SingleJson
from soar_sdk.SiemplifyLogger import SiemplifyLogger

from okta.core.exceptions import HTTPException
from okta.core.utils import get_full_url, validate_response, get_access_token
from okta.core.constants import (
    API_TOKEN_AUTH_METHOD,
    BEGIN_MARKER,
    BEGIN_PRIVATE_KEY,
    END_MARKER,
    END_PRIVATE_KEY,
    OAUTH2_AUTH_METHOD,
)

HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}
CURRENT_USER = "/users/me"  # X
LIST_USERS = "/users"  # VA
LIST_USER_GROUPS = "/users/{userId}/groups"  # VVA
ADD_GROUP = "/groups"  # VA
RESET_PASSWORD = "/users/{userId}/lifecycle/reset_password"  # VVA
SET_PASSWORD = "/users/{userId}"  # VVA
SUSPEND_USER = "/users/{userId}/lifecycle/suspend"  # VVA
UNSUSPEND_USER = "/users/{userId}/lifecycle/unsuspend"  # VVA
DEACTIVATE_USER = "/users/{userId}/lifecycle/deactivate"
REACTIVATE_USER = "/users/{userId}/lifecycle/activate"
GET_USER = "/users/{userId}"  # VA
GET_GROUP = "/groups/{groupId}"  # VA
LIST_PROVIDERS = "/idps"  # VA
LIST_ROLES = "/users/{userId}/roles"  # VVA
ASSIGN_ROLE = "/users/{userId}/roles"  # VVA
UNASSIGN_ROLE = "/users/{userId}/roles/{roleId}"  # VVA
CLEAR_USER_SESSIONS = "/users/{userId}/sessions"
RSA_HEADER = "-----BEGIN RSA PRIVATE KEY-----"
RSA_FOOTER = "-----END RSA PRIVATE KEY-----"
RSA_CHUNK_SIZE = 64


class OktaException(Exception):
    """
    General Exception for Okta manager
    """


class OktaManager:
    """Responsible for all Okta operations functionality"""

    def __init__(
        self,
        api_root: str,
        api_token: str | None = None,
        client_id: str | None = None,
        use_oauth_authentication: bool = False,
        key_id: str | None = None,
        private_key: str | None = None,
        logger: SiemplifyLogger | None = None,
        version: str = "v1",
        verify_ssl: bool = False,
        session: Session | None = None,
    )-> None:
        """Initialize the OktaManager

        Args:
            api_root(str): Thease URL of the Okta API.
            api_token (str | None): The API token for authentication.
            version (str): Api version string (default is 'v1').
            verify_ssl (bool): Whether to verify SSL certificates(default is False).
            logger (SiemplifyLogger | None): logger instance.
            session (Session | None): external requests.Session instance.
        """
        self.base_uri: str = api_root

        if not api_root.endswith("/"):
            api_root += "/"

        self.api_root: str = f"{api_root}api/{version}"

        self.api_token = api_token
        self.client_id = client_id
        self.use_oauth_authentication = use_oauth_authentication
        self.key_id = key_id
        self.private_key = private_key
        self.logger = logger

        self.session: Session = session or CreateSession.create_session()

        if not session:
            self.session.verify = verify_ssl

        self.session.headers.update(HEADERS)

        if self.use_oauth_authentication:
            self._init_oauth_auth()
            return

        if client_id or private_key or key_id:
            raise OktaException(
                "You have provided OAuth configuration parameters, but "
                "'Use OAuth Authentication' is not enabled."
            )

        if api_token:
            self._init_api_token_auth(api_token)
            return

        raise OktaException(
            "Unsupported authentication method. Please provide either API Token or "
            "Client ID and Private Key for OAuth2."
        )


    def _init_oauth_auth(self) -> None:
        if not self.client_id or not self.private_key:
            raise OktaException(
                "Client ID and Private Key are required for OAuth2 authentication."
            )

        self.auth_method: str = OAUTH2_AUTH_METHOD

        formatted_private_key = self.format_rsa_key(self.private_key)

        access_token = get_access_token(
            client_id=self.client_id,
            base_uri=self.base_uri,
            private_key=formatted_private_key,
            session=self.session,
            key_id=self.key_id,
        )

        self.session.headers.update(
            {"Authorization": f"Bearer {access_token}"}
        )


    def _init_api_token_auth(self, api_token: str) -> None:
        self.auth_method: str = API_TOKEN_AUTH_METHOD

        api_token = api_token.strip()

        if api_token.startswith("SSWS "):
            api_token = api_token[len("SSWS ") :].strip()

        self.session.headers.update(
            {"Authorization": f"SSWS {api_token}"}
        )

    def test_connectivity(self) -> None:
        """
        Test connection using a service-compatible endpoint

        Raises:
            OktaException: If the connectivity test fails.
        """
        if self.auth_method == OAUTH2_AUTH_METHOD:
            test_endpoint: str = f"{self.api_root}/users"
            params = {"limit": 1}
        else:
            test_endpoint: str = f"{self.api_root}{CURRENT_USER}"
            params = None

        try:
            response: Response = self.session.get(test_endpoint, params=params)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as error:
            status_code: int = (
                error.response.status_code
                if getattr(error, "response", None)
                else "N/A"
            )
            error_msg: str = f"Connectivity Test Failed with status {status_code}"
            raise HTTPException(error_msg, status_code) from error
        except Exception as error:
            raise OktaException(f"Connectivity Test Failed: {str(error)}") from error

    def list_users(self, q="", _filter="", search="", limit="", after=""):
        """
        Get the list of users
        :param: q: Finds a user that matches by firstName or lastName or email properties - e.g. q=eric {String}
        :param: _filter: Filters users with a supported expression for a subset of properties - e.g. status eq "ACTIVE" {String}
        (https://developer.okta.com/docs/api/getting_started/design_principles#filtering)
        :param: search: Searches for users with a supported filtering expression for most properties (Early Access) {String}
        :param: limit: Specifies the number of results returned (maximum 200) {Number}
        If you don't specify a value for limit, all results are returned.
        :param: after: token for pagination. May be used, if known, to bring results starting from a different page.
        An HTTP 500 status code usually indicates that you have exceeded the request timeout. Retry your request with a smaller limit and paginate the results. For more information, see Pagination.
        Treat the after cursor as an opaque value and obtain it through the next link relation. See Pagination.
        :return: JSON data
        """
        params = {}
        if q:
            params["q"] = q
        if _filter:
            params["filter"] = _filter
        if search:
            params["search"] = search
        if limit:
            try:
                limit = int(limit)
            except:
                raise OktaException("Error: Limit must be a number")
            params["limit"] = limit
        if after:
            params["after"] = after
        url = self.api_root + LIST_USERS
        lu_request = self.session.get(url, params=params)
        """try:
            lu_request.raise_for_status()
        except Exception as error:
            raise OktaException("Error: {0}".format(self.get_error(lu_request)))

        return lu_request.json()"""
        try:
            lu_request.raise_for_status()
        except Exception:
            raise OktaException(f"Error: {self.get_error(lu_request)}")
        try:
            next_url = lu_request.links.get("next", {}).get("url")
            results = lu_request.json()

            while next_url and (not limit or len(results) < limit):
                lu_request = self.session.get(next_url)
                try:
                    lu_request.raise_for_status()
                except Exception:
                    raise OktaException(f"Error: {self.get_error(lu_request)}")
                results.extend(lu_request.json())
                next_url = lu_request.links.get("next", {}).get("url")

            if limit and len(results) > limit:
                return results[:limit]

            return results

        except Exception as error:
            raise OktaException(f"Error: {error}")

    def list_user_groups(self, user_id):
        """
        Get the groups that the user is a member of
        :param: user_id: Id of user or login {String}
        :return: JSON data
        """
        params = {}
        params["id"] = user_id
        url = self.api_root + LIST_USER_GROUPS.format(userId=user_id)
        lug_request = self.session.get(url, params=params)
        try:
            lug_request.raise_for_status()
        except Exception:
            raise OktaException(f"Error: {self.get_error(lug_request)}")

        return lug_request.json()

    def add_group(self, profile):
        """
        Add a group
        :param: profile: okta:user_group profile for a new group. Containing a name and a description.
        :return: JSON data
        """
        _json = {}
        _json["profile"] = {}
        _json["profile"]["name"] = profile["name"]
        _json["profile"]["description"] = profile["description"]
        url = self.api_root + ADD_GROUP
        ag_request = self.session.post(url, json=_json)
        try:
            ag_request.raise_for_status()
        except Exception:
            if ag_request.status_code == 400:
                return None
            raise OktaException(f"Error: {self.get_error(ag_request)}")

        return ag_request.json()

    def reset_password(self, user_id, send_email_with_reset_link=False):
        """
        Generate a one-time token that can be used to reset a user's password
        User's account will be awaiting the password reset
        :param: user_id: Id of user or login {String}
        :param: send_email_with_reset_link: Sends reset password email to the user if true {Boolean}
        :return: JSON data (a link for the user to reset their password, or empty)
        """
        params = {}
        params["id"] = user_id
        params["sendEmail"] = send_email_with_reset_link
        url = self.api_root + RESET_PASSWORD.format(userId=user_id)
        rp_request = self.session.post(url, params=params)
        try:
            rp_request.raise_for_status()
        except Exception:
            raise OktaException(f"Error: {self.get_error(rp_request)}")

        return rp_request.json() or True

    def set_password(self, user_id, new_password):
        """
        Set the password of a user without validating existing credentials
        :param: user_id: Id of user or login {String}
        :param: new_password: The new password {String}
        :return: JSON data
        """
        _json = {}
        _json["credentials"] = {}
        _json["credentials"]["password"] = {}
        _json["credentials"]["password"]["value"] = new_password
        url = self.api_root + SET_PASSWORD.format(userId=user_id)
        sp_request = self.session.post(url, json=_json)
        try:
            sp_request.raise_for_status()
        except Exception:
            raise OktaException(f"Error: {self.get_error(sp_request)}")

        return sp_request.json()

    # Suspend or Deactivate
    def disable_user(self, user_id, is_deactivate, send_email_deactivate):
        """
        Disables the specified user
        :param: user_id: Id of user or login {String}
        :param: is_deactivate: Deactivate if TRUE, else Suspend {Boolean}
        :param: send_email_deactivate: Sends remail to the administrator if true {Boolean}
        :return: Bool (Empty object from okta)
        """
        params = {}
        params["userId"] = user_id
        if is_deactivate:
            params["sendEmail"] = send_email_deactivate
            url = self.api_root + DEACTIVATE_USER.format(userId=user_id)
            du_request = self.session.post(url)
        else:
            url = self.api_root + SUSPEND_USER.format(userId=user_id)
            du_request = self.session.post(url, params=params)
        try:
            du_request.raise_for_status()
        except Exception:
            raise OktaException(f"Error: {self.get_error(du_request)}")

        return True

    # Unsuspend or Activate
    def enable_user(self, user_id, is_reactivate, send_email_reactivate):
        """
        Enables the specified user
        :param: user_id: Id of user or login {String}
        :param: is_reactivate: Activate if TRUE, else Unuspend {Boolean}
        :param: send_email_reactivate: Sends email to the administrator if true {Boolean}
        :return: JSON data
        """
        params = {}
        params["id"] = user_id
        if is_reactivate:
            params["sendEmail"] = send_email_reactivate
            url = self.api_root + REACTIVATE_USER.format(userId=user_id)
            eu_request = self.session.post(url)
        else:
            url = self.api_root + UNSUSPEND_USER.format(userId=user_id)
            eu_request = self.session.post(url, params=params)
        try:
            eu_request.raise_for_status()
        except Exception:
            raise OktaException(f"Error: {self.get_error(eu_request)}")

        return True

    def get_user(self, user_id):
        """
        Get information about a user
        :param: user_id: Id of user or login {String}
        :return: Analysis ID to later be queried
        """
        url = self.api_root + GET_USER.format(userId=user_id)
        gu_request = self.session.get(url)
        try:
            gu_request.raise_for_status()
        except Exception:
            if gu_request.status_code == 404:
                return None
            raise OktaException(f"Error: {self.get_error(gu_request)}")

        return gu_request.json()

    def get_group(self, group_id):
        """
        Get information about a group
        :param: group_id: Id of group {String}
        :return: JSON data
        """
        params = {}
        params["id"] = group_id
        url = self.api_root + GET_GROUP.format(groupId=group_id)
        gg_request = self.session.get(url)
        try:
            gg_request.raise_for_status()
        except Exception:
            if gg_request.status_code == 404:
                return None
            raise OktaException(f"Error: {self.get_error(gg_request)}")

        return gg_request.json()

    def list_providers(self, q="", _type="", limit="", after=""):
        """
        List identity providers (IdPs) in your organization
        :param: q: Searches the name property of IdPs for matching value (startswith) {String}
        :param: _type: Filters IdPs by type {String}
        :param: limit: Specifies the number of IdP results in a page (Default 20) {Number}
        :param: after: token for pagination. May be used, if known, to bring results starting from a different page.
        Search currently performs a startsWith match.
        SAML2       Enterprise IdP provider that supports the SAML 2.0 Web Browser SSO Profile
        FACEBOOK    Facebook Login
        GOOGLE      Google Sign-In with OpenID Connect
        LINKEDIN    Sign In with LinkedIn
        MICROSOFT   Microsoft Enterprise SSO
        :return: JSON data
        """
        params = {}
        if q:
            params["q"] = q
        if _type:
            params["type"] = _type
        if limit:
            try:
                limit = int(limit)
            except:
                raise OktaException("Error: Limit must be a number")
            params["limit"] = limit
        if after:
            params["after"] = after
        url = self.api_root + LIST_PROVIDERS
        lp_request = self.session.get(url, params=params)
        res = []
        try:
            lp_request.raise_for_status()
        except Exception:
            raise OktaException(f"Error: {self.get_error(lp_request)}")
        try:
            next_url = lp_request.links.get("next", {}).get("url")
            res = lp_request.json()
            stop = False
            while not stop:
                if limit or limit == 0:
                    if limit < len(res):
                        res = res[:limit]
                        stop = True
                        break
                if not next_url:
                    stop = True
                    break
                l, lp_request, url = self.pagination(lp_request, url)
                try:
                    lp_request.raise_for_status()
                except Exception:
                    raise OktaException(f"Error: {self.get_error(lp_request)}")
                if l:
                    res.extend(l)
                else:
                    stop = True
        except Exception as error:
            raise OktaException(f"Error: {error}")
        return res  # lp_request.json()

    def pagination(
        self,
        result: Response,
        url: str
    ) -> tuple[list[SingleJson], Response, str]:
        """
        Pagination helper

        Args:
            result: response object
            url: url for the request

        Returns:
            tuple[list[SingleJson], Response, str]: list of results, response object,
            url
        """
        response_list = list(result.json())
        next_url = result.links.get("next", {}).get("url")
        r = result

        while next_url:
            r = self.session.get(next_url)
            r.raise_for_status()
            response_list.extend(r.json())
            next_url = r.links.get("next", {}).get("url")

        return response_list, r, url

    def list_roles(self, user_id):
        """
        Lists all roles assigned to a user
        :param: user_id: Id of user {String}
        :return: JSON data
        """
        params = {}
        params["userId"] = user_id
        url = self.api_root + LIST_ROLES.format(userId=user_id)
        lr_request = self.session.get(url)
        try:
            lr_request.raise_for_status()
        except Exception:
            raise OktaException(f"Error: {self.get_error(lr_request)}")

        return lr_request.json()

    def assign_role(self, user_id, _type):
        """
        Lists all roles assigned to a user
        :param: user_id: Id of user {String}
        :param: __type: type of role to assign {String}
        SUPER_ADMIN                             Super Administrator
        ORG_ADMIN                               Organizational Administrator
        API_ACCESS_MANAGEMENT_ADMIN	API          Access Management Administrator
        APP_ADMIN                               Application Administrator           (Apps)
        USER_ADMIN                              Group Administrator                 (Groups)
        MOBILE_ADMIN                            Mobile Administrator
        READ_ONLY_ADMIN	                         Read-only Administrator
        :return: JSON data
        """
        params = {}
        params["userId"] = user_id
        params["type"] = _type
        url = self.api_root + ASSIGN_ROLE.format(userId=user_id)
        ar_request = self.session.post(url, json={"type": _type})
        try:
            ar_request.raise_for_status()
        except Exception:
            if ar_request.status_code == 409:
                return None
            raise OktaException(f"Error: {self.get_error(ar_request)}")

        return ar_request.json()

    def unassign_role(self, user_id, role_id):
        """
        Unassign a role from a user
        :param: user_id: Id of user {String}
        :param: role_id: Id of role to unassign {String}
        :return: JSON data
        """
        params = {}
        params["userId"] = user_id
        params["roleId"] = role_id
        url = self.api_root + UNASSIGN_ROLE.format(userId=user_id, roleId=role_id)
        ur_request = self.session.delete(url)
        try:
            ur_request.raise_for_status()
        except Exception:
            if ur_request.status_code == 404:
                return None
            raise OktaException(f"Error: {self.get_error(ur_request)}")

        return True

    @staticmethod
    def format_rsa_key(key_string: str | None) -> str:
        """Formats an RSA private key string into PEM format with header, footer
        and line breaks.

        Args:
            key_string (str | None): The unformatted RSA private key string.

        Returns:
            str: The formatted RSA PEM-formatted RSA private key string.
        """
        key_string: str = key_string.strip()

        if BEGIN_MARKER in key_string and END_MARKER in key_string:
            lines: List[str] = key_string.splitlines()
            header: str = ""
            footer: str = ""
            content_lines: List[str] = []

            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if line.startswith(BEGIN_MARKER):
                    header = line
                elif line.startswith(END_MARKER):
                    footer = line
                else:
                    content_lines.append(line)

            if header and footer:
                content: str = "".join(content_lines)
                key_chunks: List[str] = [
                    content[i : i + RSA_CHUNK_SIZE] + "\n"
                    for i in range(0, len(content), RSA_CHUNK_SIZE)
                ]

                return f"{header}\n" + "".join(key_chunks) + f"{footer}\n"

        key_string: str = (
            key_string.replace(RSA_HEADER, "")
            .replace(RSA_FOOTER, "")
            .replace(BEGIN_PRIVATE_KEY, "")
            .replace(END_PRIVATE_KEY, "")
        )
        key_string: str = (
            key_string.replace("\n", "").replace("\r", "").replace(" ", "")
        )

        key_chunks: List[str] = [
            key_string[i : i + RSA_CHUNK_SIZE] + "\n"
            for i in range(0, len(key_string), RSA_CHUNK_SIZE)
        ]

        formatted_key: List[str] = (
            [f"{RSA_HEADER}\n"] + key_chunks + [f"{RSA_FOOTER}\n"]
        )

        return "".join(formatted_key)

    def _prepare_itp_signal_payload(
        self,
        timestamp: str,
        user_email: str,
        reason: str,
        severity: str,
        data_issuer_url: str,
    ) -> SingleJson:
        """Prepare the payload for the ITP signal.

        Args:
            timestamp: Event detection timestamp(ISO 8601 format).
            user_email: Email of the affected user.
            reason: Reason for the risk signal.
            severity: Risk severity level.
            data_issuer_url: Creation source of the signal.

        Returns:
            SingleJson: The payload for the ITP signal.
        """
        event_milliseconds = self._parse_itp_signal_timestamp(timestamp)
        return {
            "iss": data_issuer_url,
            "jti": str(uuid.uuid1()),
            "iat": int(time.time()),
            "aud": self.base_uri.rstrip("/"),
            "events": {
                "https://schemas.okta.com/secevent/okta/event-type/user-risk-change": {
                    "subject": {"user": {"format": "email", "email": user_email}},
                    "current_level": severity.lower(),
                    "previous_level": "low",
                    "reason_admin": {"en": reason},
                    "event_timestamp": event_milliseconds,
                }
            },
        }

    @staticmethod
    def _parse_itp_signal_timestamp(timestamp: str) -> int:
        """
        Parse the timestamp string and return milliseconds.

        Args:
            timestamp: Event detection timestamp(ISO 8601 format).

        Returns:
            int: Timestamp in milliseconds.
        """
        formats = [
            "%Y-%m-%dT%H:%M:%SZ",  # Without milliseconds
            "%Y-%m-%dT%H:%M:%S.%fZ"  # With milliseconds
        ]
        for fmt in formats:
            try:
                parsed_timestamp = datetime.strptime(timestamp, fmt)
                return int(parsed_timestamp.timestamp() * 1000)
            except ValueError:
                continue

        raise OktaException(
            "Failed to send the ITP Signal to Okta: invalid timestamp"
        )

    def _send_itp_signal_request(
        self, encoded_data: str, payload: SingleJson
    ) -> SingleJson:
        """
        Send the ITP signal request to Okta.

        Args:
            encoded_data: The encoded JWT data.

        Returns:
            SingleJson: JSON response data.
        """
        json_results: SingleJson = {"status": None, "payload": {}}

        request_url = get_full_url(
            api_root=self.base_uri, endpoint_id="send_itp_signal"
        )
        request_headers = {
            "Accept": "application/json",
            "Content-Type": "application/secevent+jwt",
        }
        request_attributes = {
            "url": request_url,
            "data": encoded_data,
            "headers": request_headers,
        }
        response = self.session.post(**request_attributes)
        validate_response(response, error_msg="Failed to send the ITP Signal to Okta")
        json_results["status"] = response.status_code
        json_results["payload"] = payload
        return json_results

    def sent_itp_signal(
        self,
        key_id: str,
        private_key_string: str,
        timestamp: str,
        user_email: str,
        reason: str,
        severity: str,
        data_issuer_url: str,
    ) -> SingleJson:
        """
        Send ITP signal to Okta RISC API using signed JWT.

        Args:
            key_id: ID of the signing key for JWT.
            private_key_string: RSA private key string.
            timestamp: Event detection timestamp(ISO 8601 format).
            user_email: Email of the affected user.
            reason: Reason for the risk signal.
            severity: Risk severity level.
            data_issuer_url: Creation source of the signal.

        Returns:
            SingleJson: JSON response data.
        """
        private_key = self.format_rsa_key(private_key_string)

        payload = self._prepare_itp_signal_payload(
            timestamp, user_email, reason, severity, data_issuer_url
        )

        encoded_data = jwt.encode(
            payload,
            private_key,
            algorithm="RS256",
            headers={
                "kid": key_id,  # Key ID for Okta to verify signature
                "typ": "secevent+jwt",  # Token type
            },
        )

        self.logger.info(encoded_data)
        return self._send_itp_signal_request(encoded_data, payload)

    def list_groups(self, q="", _filter="", search="", limit="", after=""):
        """
        Get the list of groups - not an action
        :param: q: Searches the name property of groups for matching value {String}
        :param: _filter: Filter expression for groups {String}
        :param: search: Searches for users with a supported filtering expression for most properties (Early Access) {String}
        :param: limit: Specifies the number of group results in a page (Default 10000) {Number}
        :param: after: token for pagination. May be used, if known, to bring results starting from a different page.
        :return: JSON data
        """
        params = {}
        if q:
            params["q"] = q
        if _filter:
            params["filter"] = _filter
        if search:
            params["search"] = search
        if limit:
            try:
                limit = int(limit)
            except:
                raise OktaException("Error: Limit must be a number")
            params["limit"] = limit
        if after:
            params["after"] = after
        url = self.api_root + ADD_GROUP
        lg_request = self.session.get(url, params=params)
        """try:
            lg_request.raise_for_status()
        except Exception as error:
            raise OktaException("Error: {0}".format(self.get_error(lg_request)))"""
        res = []
        try:
            lg_request.raise_for_status()
        except Exception:
            raise OktaException(f"Error: {self.get_error(lg_request)}")
        try:
            next_url = lg_request.links.get("next", {}).get("url")
            res = lg_request.json()
            stop = False
            while not stop:
                if limit or limit == 0:
                    if limit < len(res):
                        res = res[:limit]
                        stop = True
                        break
                if not next_url:
                    stop = True
                    break
                l, lg_request, url = self.pagination(lg_request, url)
                try:
                    lg_request.raise_for_status()
                except Exception:
                    raise OktaException(f"Error: {self.get_error(lg_request)}")
                if l:
                    res.extend(l)
                else:
                    stop = True
        except Exception as error:
            raise OktaException(f"Error: {error}")
        # return lg_request.json() #res
        return res  # lp_request.json()

    def login_to_id(self, login):
        """
        Transform user login into id - not an action
        :return: String
        """
        user = self.get_user(login)
        if user:
            return user["id"]
        else:
            return None

    def find_role_id_by_name(self, user_id, role_name):
        """
        Find role name -> id for a user - not an action
        :return: String
        """
        roles = self.list_roles(user_id)
        if roles:
            for role in roles:
                if role["type"] == role_name:
                    return role["id"]
                else:
                    continue
        else:
            return None

    def get_error(self, response):
        """
        Handle errors' messages - not an action
        :return: String
        """
        m = ""
        try:
            j = json.loads(response.text)
            if "errorCauses" in j:
                if j["errorCauses"]:
                    for i in j["errorCauses"]:
                        if "errorSummary" in i:
                            m += i["errorSummary"] + "\n"
                else:
                    if "errorSummary" in j:
                        m = j["errorSummary"]
            else:
                if "errorSummary" in j:
                    m = j["errorSummary"]
        except:
            m = response.text
            pass
        if not m:
            m: str = (
                f"HTTP {response.status_code} {response.reason}"
                if not response.text
                else response.text
            )
        return m

    def clear_user_sessions(self, user_id: str) -> bool:
        """
        Clear all sessions for a user.
        This will log the user out of all active Okta sessions.

        Args:
            user_id (str): The ID or login of the user.

        Returns:
            bool: True if the sessions were cleared successfully.
        """
        url: str = self.api_root + CLEAR_USER_SESSIONS.format(userId=user_id)
        response: Response = self.session.delete(url)
        validate_response(response, f"Failed to clear sessions for user {user_id}")

        return True
