# -*- coding: utf-8 -*-
from __future__ import annotations
import json

from requests import Session
from urllib.parse import urljoin


class APIError(Exception):
    """An error with the data received within a valid HTTP response."""


class Client:
    """Communicate with an ePO server.
    Instances are callable, pass a command name and parameters to make
    API calls.
    """

    def __init__(self, url, username, password, session=None):
        """Create a client for the given ePO server.
        :param url: Location of ePO server.
        :param username: Username to authenticate.
        :param password: Password to authenticate.
        :param session: Custom instance of :class:`requests.Session`,
            useful for configuring server verification.
        """
        self.url = url
        self.username = username
        self.password = password

        if session is None:
            session = Session()

        self._session = session
        self._token = None

    def _get_token(self, _skip=False):
        """Get the security token if it's not already cached.
        :param bool _skip: Used internally when making the initial
            request to get the token.
        """

        if self._token is None and not _skip:
            self._token = self._request("core.getSecurityToken")

        return self._token

    def _request(self, name, **kwargs):
        """Format the request and interpret the response.
        Usually you want to use :meth:`__call__` instead.
        :param name: ePO command name to call.
        :param kwargs: Arguments passed to :meth:`requests.request`.
        :return: Deserialized JSON data.
        """

        kwargs.setdefault("auth", (self.username, self.password))
        params = kwargs.setdefault("params", {})
        # Check whether the response will be JSON.
        is_json = params.setdefault(":output", "json") == "json"
        # Add the security token, unless this is the request to get it.
        # params.setdefault(
        #     "orion.user.security.token",
        #     self._get_token(_skip=name == "core.getSecurityToken"),
        # )
        url = urljoin(self.url, f"remote/{name}")

        if any(kwargs.get(key) for key in ("data", "json", "files")):
            # Use post method if there is post data.
            r = self._session.post(url, **kwargs)
        else:
            r = self._session.get(url, **kwargs)

        # Check that there was a valid HTTP response.
        r.raise_for_status()
        text = r.text

        if not text.startswith("OK:"):
            # The response body contains an error.
            raise APIError(text)

        # Strip "OK:" from response and parse JSON if needed.
        return json.loads(text[3:]) if is_json else text[3:]

    def __call__(self, name, *args, **kwargs):
        """Make an API call by calling this instance.
        Collects arguments and calls :meth:`_request`.
        ePO commands take positional and named arguments. Positional
        arguments are internally numbered "param#" and passed as named
        arguments.
        Files can be passed to some commands. Pass a dictionary of
        ``'filename': file-like objects``, or other formats accepted by
        :meth:`requests.request`. This command will not open files, as
        it is better to manage that in a ``with`` block from the calling
        code.
        :param name: ePO command name to call.
        :param args: Positional arguments to the command.
        :param kwargs: Named arguments to the command.
        :param dict params: Named arguments that are not valid Python
            names can be provided here.
        :param dict files: Files to upload to the command.
        :return: Deserialized JSON data.
        """
        params = kwargs.pop("params", {})
        files = kwargs.pop("files", {})

        for i, item in enumerate(args, start=1):
            params[f"param{i}"] = item

        params.update(kwargs)
        return self._request(f"{name}", params=params, files=files)
