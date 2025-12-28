from __future__ import annotations

import json

import requests
from furl import furl
from requests.auth import AuthBase


class TimeoutError(Exception):
    pass


class ConnectionError(Exception):
    pass


class AuthenticationError(Exception):
    pass


class DockerHubAuth(AuthBase):
    def __init__(
        self,
        requests_post,
        api_url,
        username=None,
        password=None,
        token=None,
        delete_creds=True,
    ):
        """Args:
        requests_post (:py:meth:`DockerHub._do_requests_post`):
        api_url (str):
        username (str, optional):
        password (str, optional):
        token (str, optional):
        delete_creds (bool, optional):

        """
        self._api_url = api_url
        self._requests_post = requests_post
        if token is not None:
            self._token = token
            return
        if username is not None and password is not None:
            self._username = username
            self._password = password
            self._get_authorization_token()
            if delete_creds:
                self._username = None
                self._password = None
            return
        raise ValueError(
            "Need either username and password or token for authentication",
        )

    @property
    def token(self):
        return self._token

    def __eq__(self, other):
        return self._token == getattr(other, "_token", None)

    def __ne__(self, other):
        return not self == other

    def __call__(self, r):
        r.headers["Authorization"] = f"JWT {self._token}"
        return r

    def _get_authorization_token(self):
        """Actually gets the authentication token
        Raises:
            AuthenticationError: didn't login right
        """
        resp = self._requests_post(
            self._api_url,
            {"username": self._username, "password": self._password},
        )
        if not resp.ok:
            raise AuthenticationError(
                f"Error Status {resp.status_code}:\n{json.dumps(resp.json(), indent=2)}",
            )
        self._token = resp.json()["token"]


def parse_url(url):
    """Parses a url into the base url and the query params
    Args:
        url (str): url with query string, or not
    Returns:
        (str, `dict` of `lists`): url, query (dict of values)
    """
    f = furl(url)
    query = f.args
    query = {a[0]: a[1] for a in query.listitems()}
    f.remove(query=True).path.normalize()
    url = f.url

    return url, query


def user_cleaner(user):
    """Converts none or _ to library, makes username lowercase
    Args:
        user (str):
    Returns:
        str: cleaned username
    """
    if user in ("_", ""):
        return "library"
    try:
        return user.lower()
    except AttributeError:
        return user


class DockerHub:
    """Actual class for making API calls
    Args:
        username (str, optional):
        password(str, optional):
        token(str, optional):
        url(str, optional): Url of api (https://hub.docker.com)
        version(str, optional): Api version (v2)
        delete_creds (bool, optional): Whether to delete password after logging in (default True)
    """

    def __init__(
        self,
        username=None,
        password=None,
        token=None,
        url=None,
        version="v2",
        delete_creds=True,
    ):
        self._version = version
        self._url = f"{url or 'https://hub.docker.com'}/{self.version}"
        self._session = requests.Session()
        self._auth = None
        self._token = None
        self._username = None
        self._password = None
        self._cookies = {}
        self._debug = False
        self.login(username, password, token, delete_creds)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self._session.close()

    @property
    def username(self):
        if self._username is None and self.logged_in:
            self._get_username()
        return self._username

    @property
    def logged_in(self):
        return self.token is not None

    @property
    def version(self):
        return self._version

    @property
    def url(self):
        return self._url

    @property
    def token(self):
        return self._token

    @token.setter
    def token(self, value):
        self._token = value
        self._get_username()

    def _do_request(self, method, address, **kwargs):
        try:
            if "timeout" not in kwargs:
                kwargs["timeout"] = (5, 15)

            if "auth" not in kwargs:
                kwargs["auth"] = self._auth

            if "headers" not in kwargs:
                kwargs["headers"] = {"Content-Type": "application/json"}
            elif "Content-Type" not in kwargs["headers"]:
                kwargs["headers"]["Content-Type"] = "application/json"

            # MOST IMPORTANT HACK...
            if self._session.cookies.get("csrftoken"):
                kwargs["headers"]["X-CSRFToken"] = self._session.cookies.get(
                    "csrftoken",
                )

            url, query = parse_url(address)
            if query:
                address = url
                if "params" in kwargs:
                    query.update(kwargs["params"])
                kwargs["params"] = query

            resp = self._session.request(method, address, **kwargs)
        except requests.exceptions.Timeout as e:
            raise TimeoutError(f"Connection Timeout. Download failed: {e}")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Connection Error. Download failed: {e}")
        else:
            resp.raise_for_status()
            return resp

    def _do_requests_get(self, address, **kwargs):
        if "params" not in kwargs:
            kwargs["params"] = {}
        if "perPage" not in kwargs["params"]:
            kwargs["params"]["perPage"] = 100
        return self._do_request("GET", address, **kwargs)

    def _do_requests_post(self, address, json_data=None, **kwargs):
        return self._do_request("POST", address, json=json_data, **kwargs)

    def _api_url(self, path):
        return f"{self.url}/{path}/"

    def _api_url_without_version(self, path):
        return f"https://hub.docker.com/{path}"

    def _get_username(self):
        if self.logged_in:
            self._username = user_cleaner(self.logged_in_user()["username"])
        else:
            self._username = None

    def login(self, username=None, password=None, token=None, delete_creds=True):
        """Logs into Docker hub and gets a token
        Either username and password or token should be specified
        Args:
            username (str, optional):
            password (str, optional):
            token (str, optional):
            delete_creds (bool, optional):
        Returns:
        """
        self._username = user_cleaner(username)
        self._password = password
        self._token = token
        if token is not None:
            # login with token
            self._auth = DockerHubAuth(
                self._do_requests_post,
                self._api_url("users/login"),
                token=token,
            )
        elif username is not None and password is not None:
            # login with user/pass
            self._auth = DockerHubAuth(
                self._do_requests_post,
                self._api_url("users/login"),
                username=username,
                password=password,
            )
        else:
            # don't login
            return

        if delete_creds:
            self._password = None
        self._token = self._auth.token

    def user(self, user, **kwargs):
        user = user_cleaner(user)
        url = self._api_url(f"users/{user}")
        return self._do_requests_get(url, **kwargs).json()

    def logged_in_user(self):
        """Returns: logged in user"""
        return self._do_requests_get(self._api_url("user")).json()

    def send_invite(self, org, team, email):
        """Send invitation for a new user in a team
        :param org: Organization
        :param team: Team
        :param email: Email tosend invite
        """
        url = self._api_url(f"orgs/{org}/groups/{team}/members")
        return self._do_requests_post(url, {"member": email.lower()})

    def test_connectivity(self):
        url = self._api_url("_catalog")
        return self._do_requests_get(url)
