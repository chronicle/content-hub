from __future__ import annotations

import base64
import time
import uuid
from copy import deepcopy
from typing import TYPE_CHECKING
from urllib.parse import quote, urlencode

import jwt
import requests
from OpenSSL import crypto

if TYPE_CHECKING:
    from datetime import datetime

TOKEN_PAYLOAD = {
    "client_id": None,
    "scope": "https://graph.microsoft.com/.default",
    "client_secret": None,
    "grant_type": "client_credentials",
}

HEADERS = {"Content-Type": "application/json"}
UPDATE_ALERT_HEADER = {"Prefer": "return=representation"}
UPDATE_ALERT_KEY = "Prefer"
INVALID_REFRESH_TOKEN_ERROR = "Refresh Token is malformed or invalid"

GRANT_TYPE = "client_credentials"
SCOPE = "https://graph.microsoft.com/.default"
CLIENT_ASSERTION_TYPE = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"

# urls
URL_AUTHORIZATION = "https://login.microsoftonline.com/{tenant}/adminconsent?client_id={client_id}&redirect_uri={redirect_uri}"
ACCESS_TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
GET_ALERT_URL = "https://graph.microsoft.com/v1.0/security/alerts"
GET_MFA_STATS_URL = (
    "https://graph.microsoft.com/beta/reports/credentialUserRegistrationDetails"
)
GET_MAIL_RULES_URL = (
    "https://graph.microsoft.com/v1.0/users/{}/mailFolders/inbox/messageRules"
)
MESSAGE_URL = "https://graph.microsoft.com/v1.0/users/{}/messages/{}"
LIST_MESSAGES_URL = "https://graph.microsoft.com/v1.0/users/{}/messages"
LIST_ATTACHMENTS_URL = (
    "https://graph.microsoft.com/v1.0/users/{}/messages/{}/attachments"
)
DELETE_ATTACHMENTS_URL = (
    "https://graph.microsoft.com/v1.0/users/{}/messages/{}/attachments/{}"
)
TI_INDICATORS_URL = "https://graph.microsoft.com/beta/security/tiIndicators/{}"
GET_SECURE_SCORE_URL = "https://graph.microsoft.com/beta/security/secureScores"

TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


# =====================================
#              CLASSES                #
# =====================================


class MicrosoftGraphSecurityManagerError(Exception):
    """General Exception for microsoft graph security manager"""


class MicrosoftGraphSecurityManager:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        certificate_path: str,
        certificate_password: str,
        tenant: str,
        verify_ssl: bool = False,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.certificate_path = certificate_path
        self.certificate_password = certificate_password
        self.tenant = tenant
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.access_token: str = self.generate_token(
            self.client_id,
            self.client_secret,
            self.certificate_path,
            self.certificate_password,
            self.tenant,
        )
        self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})

    def generate_token(
        self,
        client_id: str,
        client_secret: str,
        certificate_path: str,
        certificate_password: str,
        tenant: str,
    ) -> str:
        """Request access token
        :param client_id: {string} The Application ID that the registration portal
        :param client_secret: {string} The application secret that you created in the app registration portal for your app.
        :param certificate_path: {string} If authentication based on certificates is used instead of client secret, specify path to the certificate on Siemplify server..
        :param certificate_password: {string} If certificate is password-protected, specify the password to open the certificate file.
        :param tenant: {string} domain name from azure portal
        :return: {string} Access token. The app can use this token in calls to Microsoft Graph.
        """
        if client_secret:
            return self.generate_token_by_client_secret(
                client_id,
                client_secret,
                tenant,
            )

        return self.generate_token_by_certificate(
            client_id,
            certificate_path,
            certificate_password,
            tenant,
        )

    @staticmethod
    def generate_token_by_client_secret(
        client_id: str,
        client_secret: str,
        tenant: str,
    ) -> str:
        """Request access token by client secret (Valid for 60 min)
        :param client_id: {string} The Application ID that the registration portal
        :param client_secret: {string} The application secret that you created in the app registration portal for your app
        :param tenant: {string} domain name from azure portal
        :return: {string} Access token. The app can use this token in calls to Microsoft Graph
        """
        payload = deepcopy(TOKEN_PAYLOAD)
        payload["client_id"] = client_id
        payload["client_secret"] = client_secret
        res = requests.post(ACCESS_TOKEN_URL.format(tenant=tenant), data=payload)
        MicrosoftGraphSecurityManager.validate_response(res)
        return res.json().get("access_token")

    def generate_token_by_certificate(
        self,
        client_id,
        certificate_path,
        certificate_password,
        tenant,
    ):
        """Request access token by certificate (Valid for 60 min)
        :param client_id: {string} The Application ID that the registration portal
        :param certificate_path: {string} If authentication based on certificates is used instead of client secret, specify path to the certificate on Siemplify server
        :param certificate_password: {string} If certificate is password-protected, specify the password to open the certificate file
        :param tenant: {string} domain name from azure portal
        :return: {string} Access token. The app can use this token in calls to Microsoft Graph
        """
        thumbprint, private_key = self.get_certificate_thumbprint_and_private_key(
            certificate_path,
            certificate_password,
        )
        jwt_token = self.get_jwt_token(client_id, tenant, thumbprint, private_key)

        params = {
            "grant_type": GRANT_TYPE,
            "scope": SCOPE,
            "client_id": client_id,
            "client_assertion_type": CLIENT_ASSERTION_TYPE,
            "client_assertion": jwt_token,
        }

        response = requests.post(ACCESS_TOKEN_URL.format(tenant=tenant), data=params)
        MicrosoftGraphSecurityManager.validate_response(response)
        return response.json().get("access_token")

    def get_certificate_thumbprint_and_private_key(
        self,
        certificate_path,
        certificate_password,
    ):
        """Get thumbprint and private key from certificate
        :param certificate_path: {string} If authentication based on certificates is used instead of client secret, specify path to the certificate on Siemplify server
        :param certificate_password: {string} If certificate is password-protected, specify the password to open the certificate file
        :return: {tuple} The certificate thumbprint and private key
        """
        try:
            with open(certificate_path, "rb") as pfx:
                certificate = crypto.load_pkcs12(pfx.read(), certificate_password)
                private_key_object = certificate.get_privatekey()
                x509_certificate = certificate.get_certificate()
                thumbprint_bytes = x509_certificate.digest("sha1")
                # Remove colons from thumbprint
                thumbprint = thumbprint_bytes.decode("utf-8").replace(":", "")
                private_key = crypto.dump_privatekey(
                    crypto.FILETYPE_PEM,
                    private_key_object,
                )

                return thumbprint, private_key
        except Exception:
            raise MicrosoftGraphSecurityManagerError("Unable to read certificate file")

    def get_jwt_token(self, client_id, tenant, thumbprint, private_key):
        """Get JWT token
        :param client_id: {string} The Application ID that the registration portal
        :param tenant: {string} domain name from azure portal
        :param thumbprint: {string} The certificate thumbprint
        :param private_key: The certificate private key
        :return: {bytes} The JWT token
        """
        # Encode hex to Base64
        encoded_thumbprint = base64.b64encode(bytes.fromhex(thumbprint)).decode("utf-8")
        # Perform base64url-encoding as per RFC7515 Appendix C
        x5t = encoded_thumbprint.replace("=", "").replace("+", "-").replace("/", "_")
        current_timestamp = int(time.time())

        payload = {
            "aud": ACCESS_TOKEN_URL.format(tenant=tenant),
            "exp": current_timestamp + 3600,
            "iss": client_id,
            "jti": str(uuid.uuid1()),
            "nbf": current_timestamp,
            "sub": client_id,
        }

        jwt_token = jwt.encode(
            payload,
            private_key,
            algorithm="RS256",
            headers={"x5t": x5t},
        )
        return jwt_token.decode("utf-8")

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """Validate response
        :param response: {requests.Response} The response to validate
        :param error_msg: {unicode} Default message to display on error
        """
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            raise MicrosoftGraphSecurityManagerError(
                f"{error_msg}: {error} {response.content}",
            )

    @staticmethod
    def _build_api_parameters(
        provider_list: list = None,
        severity_list: list = None,
        status_list: list = None,
        start_time: datetime = None,
        asc: bool = True,
    ) -> dict:
        """Build the parameters dict for API call
        :param provider_list: {list} List of provider names to filter with
        :param severity_list: {list} List of severities to filter with
        :param status_list: {list} List of statuses to filter with
        :param start_time: {str} Start time to filter with
        :param asc: {bool} Whether to return the results ascending or descending
        :return: {dict} The params dict
        """
        filter_params = []

        if provider_list:
            provider_filter_group = " or ".join(
                map(lambda x: f"(vendorInformation/provider eq '{x}')", provider_list),
            )
            filter_params.append(f"({provider_filter_group})")

        if severity_list:
            severity_filter_group = " or ".join(
                map(lambda x: f"(severity eq '{x}')", severity_list),
            )
            filter_params.append(f"({severity_filter_group})")

        if status_list:
            status_filter_group = " or ".join(
                map(lambda x: f"(status eq '{x}')", status_list),
            )
            filter_params.append(f"({status_filter_group})")

        if start_time:
            filter_params.append(
                f"createdDateTime gt {start_time.strftime(TIME_FORMAT)}",
            )

        # Apply filtering in oData format
        params = {
            "$filter": " and ".join(filter_params) if filter_params else None,
            "$orderby": f"createdDateTime {'asc' if asc else 'desc'}",
        }

        return params

    def get_mfa_stats(self):
        """Retrieve a list of users objects.
        :return: {list} of alerts {dicts}
        """
        res = self.session.get(GET_MFA_STATS_URL)
        self.validate_response(res)
        return res.json().get("value", [])

    def get_secure_score(self):
        """Retrieve a list of users objects.
        :return: {list} of alerts {dicts}
        """
        res = self.session.get(GET_SECURE_SCORE_URL)
        self.validate_response(res)
        return res.json().get("value", [])

    def get_user_mfa_stats(self, username):
        """Retrieve a list of users objects.
        :return: {list} of alerts {dicts}
        """
        data = self.get_mfa_stats()
        for user in data:
            if user["userPrincipalName"].lower() == username.lower():
                return user

        return None

    def get_mail_rules(self, username):
        """Retrieve a list of rule objects.
        :return: {list} of rules {dicts}
        """
        res = self.session.get(GET_MAIL_RULES_URL.format(str(username)))
        self.validate_response(res)
        return res.json().get("value", [])

    def get_message(self, username, mail_id):
        """Retrieve a message.
        :return: {list} of alerts {dicts}
        """
        res = self.session.get(MESSAGE_URL.format(str(username), str(mail_id)))
        self.validate_response(res)
        return res.json()

    def get_ti_indicator(self, indicators):
        """NOTE: Not in use yet as the API endpoint doesn't seem to be working,
        Likely because it's still in Beta. I'll update once it starts working
        with relevant actions.
        Query Azure/Defender ATP for a threat indicator.
        :param user_id: {str} The identifier of the user to kill
        :return: {list} A list of TI match information {dicts}
        """
        results = []
        ioc_list = indicators.split(",")

        for ioc in ioc_list:
            res = self.session.get(TI_INDICATORS_URL.format(str(ioc)))
            self.validate_response(res)
            results.append(res.json())

        return results

    def list_messages(self, username, filter_select, query_params):
        """Retrieve a message.
        :return: {list} of alerts {dicts}
        """
        query_string = LIST_MESSAGES_URL.format(str(username))

        query_params_list = []

        # Messy but it works
        ## Need to format the query string correctly
        ## regardless of combination of filters given
        if filter_select:
            filter_select = "$select=" + filter_select
            query_params_list.append(filter_select)
        if query_params:
            query_params = self.encode_string(query_params)
            query_params_list.append(query_params)

        if len(query_params_list) > 0:
            index = 0
            for filter_string in query_params_list:
                if index == 0:
                    query_string += "?"
                query_string += filter_string
                if index != len(query_params_list) - 1:
                    query_string += "&"
                index += 1

        res = self.session.get(query_string)
        self.validate_response(res)
        return res.json().get("value", [])

    def list_attachments(self, username, mail_id):
        """Retrieve a list of attachments from a give message ID.
        :return: {list} of attachments {dicts}
        """
        res = self.session.get(LIST_ATTACHMENTS_URL.format(str(username), str(mail_id)))
        self.validate_response(res)
        return res.json().get("value", [])

    def delete_attachment(self, username, mail_id, attachment_id):
        """Delete attachment from an email using given ID's.
        :return: HTTP 204 No Content
        """
        res = self.session.delete(
            DELETE_ATTACHMENTS_URL.format(
                str(username),
                str(mail_id),
                str(attachment_id),
            ),
        )
        if res.status_code == 204:
            response = {
                "status_code": "204",
                "result": "success",
                "output_message": "Deletion request completed successfully",
            }
        else:
            response = {
                "status_code": "" + str(res.status_code),
                "result": "failed",
                "output_message": "Deletion request failed",
            }

        return response

    def delete_message(self, username, mail_id):
        """Delete attachment from an email using given ID's.
        :return: HTTP 204 No Content
        """
        if "," in username:
            usernames = username.split(",")
            for user_id in usernames:
                res = self.session.delete(
                    MESSAGE_URL.format(str(user_id), str(mail_id)),
                )
        else:
            res = self.session.delete(MESSAGE_URL.format(str(username), str(mail_id)))

        if res.status_code == 204:
            response = {
                "status_code": "204",
                "result": "success",
                "output_message": "Deletion request completed successfully",
            }
        else:
            response = {
                "status_code": "" + str(res.status_code),
                "result": "failed",
                "output_message": "Deletion request failed",
            }

        return response

    def encode_params(self, url_params):
        """Encode a given set of parameters
        :param url_params: {dict} Dictionary of params to encode
        :return: {sting} Encoded param string
        """
        return urlencode(url_params, quote_via=quote)

    def encode_string(self, plain_string):
        """Encode a given string
        :param plain_string: {string} Plain, unencoded string
        :return: {sting} Encoded string
        """
        encoded_string = quote(plain_string)
        # Return filter selector to original state
        if encoded_string.startswith("%24filter%3D"):
            encoded_string = encoded_string.replace("%24filter%3D", "$filter=")
        return encoded_string

    def parse_quotes(self, string_param):
        """Escape single quotes as per Microsoft documentation
        :param url_params: {string} String to check for quotes
        :return: {sting} String with escalaped single quotes
        """
        string_param = string_param.replace("'", "''")

        return string_param
