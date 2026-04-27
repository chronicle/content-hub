from __future__ import annotations
from urllib.parse import urljoin
import requests
from .constants import ENDPOINTS
from .UtilsManager import validate_response, filter_items
from .GoogleTranslateParser import GoogleTranslateParser


class GoogleTranslateManager:
    def __init__(self, api_root, api_key, verify_ssl=False, siemplify_logger=None):
        """
        The method is used to init an object of Manager class
        :param api_root: {str} API root of the Google Translate instance.
        :param api_key: {str} API key of the Google Translate account.
        :param verify_ssl: {bool} If enabled, verify the SSL certificate for the connection to the Google Translate
        server is valid.
        :param siemplify_logger: Siemplify logger
        """
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.api_key = api_key
        self.logger = siemplify_logger
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.parser = GoogleTranslateParser()

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param root_url: {str} The API root for the request
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def test_connectivity(self):
        """
        Test connectivity
        """
        request_url = self._get_full_url("ping")
        params = {"key": self.api_key}
        try:
            response = self.session.get(request_url, params=params)
        except Exception as e:
            error_text = str(e.args[0]).replace(self.api_key, "******")
            raise Exception(error_text)

        validate_response(response, self.api_key)

    def translate_text(self, source_language, target_language, text):
        """
        Translate text
        :param source_language: {str} Source language of the text
        :param target_language: {str} Target language of the text
        :param text: {str} Text to be translated
        :return: {dict} Response json
        """
        request_url = self._get_full_url("translate")
        params = {"key": self.api_key}
        payload = {
            "q": text,
            "source": source_language,
            "target": target_language,
            "format": "text",
        }
        try:
            response = self.session.post(request_url, params=params, json=payload)
        except Exception as e:
            error_text = str(e.args[0]).replace(self.api_key, "******")
            raise Exception(error_text)

        validate_response(response, self.api_key)

        return response.json()

    def get_languages(self, filter_key, filter_logic, filter_value, limit):
        """
        Get languages
        :param filter_key: {str} Filter key to use for results filtering
        :param filter_logic: {str} Filter logic
        :param filter_value: {str} Filter value
        :param limit: {str} Limit for results
        :return: {list} List of Language objects
        """
        request_url = self._get_full_url("get_languages")
        params = {"key": self.api_key}
        try:
            response = self.session.get(request_url, params=params)
        except Exception as e:
            error_text = str(e.args[0]).replace(self.api_key, "******")
            raise Exception(error_text)

        validate_response(response, self.api_key)

        return filter_items(
            items=self.parser.build_languages_list(response.json()),
            filter_key=filter_key,
            filter_logic=filter_logic,
            filter_value=filter_value,
            limit=limit,
        )
