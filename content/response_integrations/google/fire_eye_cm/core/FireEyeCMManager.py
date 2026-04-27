from __future__ import annotations
import json
import defusedxml.ElementTree as ET
from typing import Optional, List
from urllib.parse import urljoin

import requests
from . import datamodels
from .FireEyeCMExceptions import (
    IncorrectHashTypeException,
    FireEyeCMUnsuccessfulOperationError,
)
from .FireEyeCMParser import FireEyeCMParser

from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon import filter_old_alerts
from .UtilsManager import validate_response, remove_empty_kwargs

from .FireEyeCMConstants import (
    PROVIDER_NAME,
    ENDPOINTS,
    HEADERS,
    API_TIME_FORMAT,
    DURATION,
    FEED_TYPE_MAPPING,
    IP_TYPE,
    URL_TYPE,
    MD5_TYPE,
    SHA256_TYPE,
    DOMAIN_TYPE,
    SHA256_LENGTH,
    MD5_LENGTH,
    ACTION_TYPE_MAPPING,
    ALERT_ID_FIELD,
    DEFAULT_MAX_EMAILS_TO_RETURN,
)


class FireEyeCMManager:
    def __init__(self, api_root, username, password, verify_ssl=False, siemplify=None):
        """
        The method is used to init an object of Manager class
        :param api_root: API Root of the FireEye CM instance.
        :param username: FireEye CM username.
        :param password: FireEye CM password.
        :param verify_ssl: If enabled, verify the SSL certificate for the connection to the FireEye CM server is valid.
        :param siemplify: (obj) An instance of the SDK SiemplifyConnectorExecution class.
        """
        self.api_root = api_root if api_root[-1:] == "/" else api_root + "/"
        self.username = username
        self.password = password
        self.siemplify = siemplify
        self.parser = FireEyeCMParser()
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.headers = HEADERS
        self.session.auth = (self.username, self.password)
        self.api_token = self.obtain_token()
        self.session.headers.update({"X-FeApi-Token": self.api_token})
        self.session.auth = None

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def obtain_token(self):
        """
        Obtain FireEye CM authentication security token.
        :return: {str} token
        """
        request_url = self._get_full_url("authorize")
        response = self.session.post(request_url)
        validate_response(response)
        return response.headers.get("X-FeApi-Token")

    def test_connectivity(self):
        """
        Test connectivity to the FireEye CM.
        :return: {bool} True if successful, exception otherwise
        """
        request_url = self._get_full_url("test_connectivity")
        response = self.session.get(request_url)
        validate_response(response, "Unable to connect to FireEye CM.")

    def get_sensor_names(self, product: str) -> List[str]:
        """
        Get sensor name of the product in FireEye CM. Checks for guest image profiles and application that are
        available on each appliance attached to the Central Management appliance.
        :param product: {str} sensor product. Possible values are MAS, wMPS, eMPS, HX..
        :return: {[str]} List of sensor names matching the desired product.
        """
        request_url = self._get_full_url("get_system_config")
        response = self.session.get(request_url)
        validate_response(
            response, error_msg=f"Failed to get sensor name for product {product}"
        )
        sys_config = self.parser.build_sys_config_obj(response.json())

        return [
            sensor.sensor_name
            for sensor in sys_config.sensors
            if sensor.os_details_product == product
        ]

    def get_alerts(self, existing_ids, start_time, duration=DURATION):
        """
        Get alerts.
        :param existing_ids: {list} The list of existing ids.
        :param start_time: {str} The datetime from where to fetch alerts.
        :param duration: {int} Duration from start time that will be used to fetch alerts.
        :return: {list} The list of Alerts.
        """
        request_url = self._get_full_url("get_alerts")
        params = {
            "duration": duration,
            "info_level": "extended",
            "start_time": self._convert_datetime_to_api_format(start_time),
        }
        response = self.session.get(request_url, params=params)
        validate_response(response)
        alerts = self.parser.build_alerts_array(response.json())
        filtered_alerts = filter_old_alerts(
            siemplify=self.siemplify,
            alerts=alerts,
            existing_ids=existing_ids,
            id_key=ALERT_ID_FIELD,
        )
        return sorted(filtered_alerts, key=lambda alert: alert.occurred_time_unix)

    def logout(self):
        """
        Logout from FireEye CM
        :return: {bool} True if successful, exception otherwise
        """
        request_url = self._get_full_url("logout")
        response = self.session.post(request_url)
        validate_response(response, "Failed to logout with token")

    @staticmethod
    def _convert_datetime_to_api_format(time):
        """
        Convert datetime object to the API time format of CM
        :param time: {datetime.Datetime} The datetime object
        :return: {unicode} The formatted time string
        """
        base_time, miliseconds_zone = time.strftime(API_TIME_FORMAT).split(".")
        return f"{base_time}.{miliseconds_zone[:3] + miliseconds_zone[-6:]}"

    def add_ioc_feed(
        self,
        entity_type,
        identifier,
        action,
        comment,
        extract_domain,
        entity_file,
        feed_name,
    ):
        """
        Add IOC feed
        :param entity_type: Entity type
        :param identifier: Entity identifier
        :param action: Action type
        :param comment: Additional comments for the feed
        :param extract_domain: If true, will extract domain from URL
        :param entity_file: Entity filepath
        :param feed_name: Name of the feed
        """
        request_url = self._get_full_url("add_ioc_feed")
        feed_data = {
            "feedName": feed_name,
            "feedType": self.map_feed_type(entity_type, extract_domain, identifier),
            "feedAction": ACTION_TYPE_MAPPING.get(action),
            "feedSource": comment if comment else "",
            "overwrite": "false",
        }
        payload = {"feed_data": json.dumps(feed_data)}
        files = [("filename", open(entity_file, "rb"))]
        self.session.headers.pop("Content-Type", None)
        response = self.session.post(request_url, data=payload, files=files)
        validate_response(response)

    def map_feed_type(self, entity_type, extract_domain, identifier):
        """
        Maps accordingly the feed type
        :param entity_type: Entity type
        :param extract_domain: If true, will extract domain from URL
        :param identifier: Entity identifier
        :return: Mapped type
        """
        if entity_type == EntityTypes.URL:
            entity_type = DOMAIN_TYPE if extract_domain else URL_TYPE
        elif entity_type == EntityTypes.ADDRESS:
            entity_type = IP_TYPE
        else:
            if len(identifier) == SHA256_LENGTH:
                entity_type = SHA256_TYPE
            elif len(identifier) == MD5_LENGTH:
                entity_type = MD5_TYPE
            else:
                raise IncorrectHashTypeException(
                    "Not supported hash type. Provide either MD5 or SHA-256."
                )
        return FEED_TYPE_MAPPING.get(entity_type)

    def acknowledge_alert(self, alert_uuid: str, annotation: str):
        """
        Acknowledge an alert
        :param alert_uuid: {str} the UUID of the alert to acknowledge
        :param annotation: {str} the annotation that explains the reason for acknowledgment.
        :return: raise Exception if failed to validate response
                 raise FireEyeCMNotFoundException if alert wasn't found
        """
        request_url = self._get_full_url("acknowledge_alert", alert_uuid=alert_uuid)
        payload = {"annotation": annotation}
        response = self.session.post(request_url, json=payload)
        validate_response(
            response,
            error_msg=f"Failed to acknowledge alert {alert_uuid} in {PROVIDER_NAME}",
        )

    def list_quarantined_emails(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        sender: Optional[str] = None,
        subject_filter: Optional[str] = None,
        limit=DEFAULT_MAX_EMAILS_TO_RETURN,
    ) -> [datamodels.QuarantinedEmail]:
        """
        List quarantined emails. If no limit is specified, 10000 will be used
        If start_time is specified than end_time should also be specified - default values are now() - 24 hours.
        :param start_time: {str} Emails that were created after start time will be returned
        :param end_time: {str} Emails that were created before end time will be returned
        :param sender: {str} The email sender
        :param subject_filter: {str} The email subject
        :param limit: {int} Total number of quarantined emails to return
        :return: {[datamodels.QuarantinedEmail]} List of Quarantined emails
        """
        request_url = self._get_full_url("list_quarantined_emails")
        params = {
            "limit": limit,
            "start_time": start_time,
            "end_time": end_time,
            "from": sender,
            "subject": subject_filter,
        }
        response = self.session.get(request_url, params=remove_empty_kwargs(params))
        validate_response(
            response, error_msg=f"Failed to List Quarantined Emails in {PROVIDER_NAME}"
        )
        return self.parser.build_quarantined_email_list(response.json(), limit=limit)

    def release_quarantined_email(self, queue_id: str, sensor_name: str):
        """
        Release quarantined email based on queue ID.
        :param queue_id: {str} the queue id of the email that needs to be released.
        :param sensor_name: {str} The sensor display name from which to release a quarantined email from.
        :return: raise FireEyeCMUnsuccessfulOperationError if failed to release quarantined email
                 raise Exception if failed to validate response
        """
        request_url = self._get_full_url("release_quarantined_email")
        response = self.session.post(
            request_url,
            params={"sensorName": sensor_name},
            json={"queue_ids": [queue_id]},
        )
        validate_response(
            response, error_msg=f"Failed to release email with queue ID {queue_id}"
        )

        # On successful email release no response should be returned
        if response.text:
            try:
                raise FireEyeCMUnsuccessfulOperationError(response.json()[queue_id])
            except FireEyeCMUnsuccessfulOperationError:
                raise
            except Exception:
                # Error is of unknown format
                raise FireEyeCMUnsuccessfulOperationError(response.text)

    def download_quarantined_email(
        self, queue_id: str, sensor_name: str
    ) -> requests.models.Response:
        """
        Download quarantined email base on queue ID.
        :param queue_id: {str} the queue id of the quarantined email that needs to be downloaded
        :param sensor_name: {str} The sensor display name from which to download a quarantined email from.
        :return: {str} The content of the downloaded email.
                 raise FireEyeCMUnsuccessfulOperationError if failed to download quarantined email, error message was found in response
                 raise Exception if failed to validate response
        """
        request_url = self._get_full_url(
            "download_quarantined_email", queue_id=queue_id
        )

        previous_header_accept = self.session.headers.get("Accept", "")
        self.session.headers.update({"Accept": "application/octet-stream"})
        response = self.session.get(request_url, params={"sensorName": sensor_name})
        self.session.headers.update({"Accept": previous_header_accept})

        content = response.text

        # Check if xml contains an error
        try:
            root = ET.fromstring(content)  # parse XML response message
            message = root.find("message")

            if message is not None:
                raise FireEyeCMUnsuccessfulOperationError(message.text or response.text)

            raise FireEyeCMUnsuccessfulOperationError(response.text)

        except FireEyeCMUnsuccessfulOperationError:
            raise

        except Exception:
            # Validate response.
            validate_response(
                response, error_msg=f"Failed to download email with queue ID {queue_id}"
            )
            # Response is valid - no XML (XML is error)
            return response

    def delete_quarantined_email(self, queue_id: str, sensor_name: str):
        """
        Delete quarantined email base on queue ID
        :param queue_id: {str} the queue id of the email that needs to be released.
        :param sensor_name: {str} The sensor from which to delete email.
        :return: raise FireEyeCMUnsuccessfulOperationError if failed to delete quarantined email
                 raise Exception if failed to validate response
        """
        request_url = self._get_full_url("delete_quarantined_email")
        response = self.session.post(
            request_url,
            params={"sensorName": sensor_name},
            json={"queue_ids": [queue_id]},
        )
        validate_response(
            response,
            error_msg=f"Failed to delete quarantined email with queue ID {queue_id}",
        )

        # On successful email deletion no response should be returned
        if response.text:
            try:
                raise FireEyeCMUnsuccessfulOperationError(response.json()[queue_id])
            except FireEyeCMUnsuccessfulOperationError:
                raise
            except Exception:
                # Error is of unknown format
                raise FireEyeCMUnsuccessfulOperationError(response.text)

    def list_ioc_feeds(self, limit: Optional[int] = None) -> [datamodels.IOCFeed]:
        """
        List custom IOC feeds on the CM for Network Security appliances only. If limit is not provided all IOC feeds will be returned.
        :param: limit: {int} Maximum IOC feeds to return
        :return: {[datamodels.IOCFeed]} List of IOC feeds datamodels.
        """
        request_url = self._get_full_url("list_ioc_feeds")
        response = self.session.get(request_url)
        validate_response(
            response, error_msg=f"Failed to list IOC feeds in {PROVIDER_NAME}"
        )
        return self.parser.build_ioc_feed_obj_list(response.json(), limit=limit)

    def delete_ioc_feed(self, feed_name: str):
        """
        Deletes custom IOC feeds from the Central Management for Network Security appliances only.
        :param feed_name: {str} The Feed name to delete
        :return: raise Exception if failed to validate response
        """
        request_url = self._get_full_url("delete_ioc_feed", feed_name=feed_name)
        response = self.session.post(request_url)
        validate_response(response, error_msg=f"Failed to delete IOC feed {feed_name}")

    def download_alert_artifacts(self, alert_uuid: str) -> requests.models.Response:
        """
        Download malware artifacts data for the specified alert ID as a zip file.
        :param alert_uuid: {str} the alert to download artifacts from
        :return: raise Exception if failed to validate response
                 raise FireEyeCMNotFoundException if alert wasn't found
        """
        request_url = self._get_full_url(
            "download_alert_artifacts", alert_uuid=alert_uuid
        )
        previous_header_accept = self.session.headers.get("Accept", "")
        self.session.headers.update({"Accept": "application/octet-stream"})
        response = self.session.get(request_url)
        self.session.headers.update({"Accept": previous_header_accept})

        validate_response(
            response,
            error_msg=f"Failed to download alert artifacts for alert UUID {alert_uuid}",
        )
        return response

    def download_custom_snort_rules_file(
        self, sensor_name: str
    ) -> requests.models.Response:
        """
        Download a custom Snort rule file from FireEye CM.
        :param sensor_name: {str} The sensor from which to download the rules file
        :return: raise FireEyeCMException if failed to download Snort rules file
        """
        request_url = self._get_full_url("download_custom_rules_file")

        previous_header_accept = self.session.headers.get("Accept", "")
        self.session.headers.update({"Accept": "application/octet-stream"})
        response = self.session.get(request_url, params={"appliance": sensor_name})
        self.session.headers.update({"Accept": previous_header_accept})

        # Check if xml contains an error
        try:
            root = ET.fromstring(response.text)  # parse XML response message
            message = root.find("description")

            if message is not None:
                raise FireEyeCMUnsuccessfulOperationError(message.text or response.text)

            raise FireEyeCMUnsuccessfulOperationError(response.text)

        except FireEyeCMUnsuccessfulOperationError:
            raise
        except Exception:
            # Validate response.
            validate_response(
                response,
                error_msg=f"Failed to download custom Snort rules files from appliance {sensor_name}",
            )
            # Response is valid - no XML (XML is error)
            return response

    def upload_custom_snort_rules_file(self, rules_file_path: str):
        """
        Upload a custom Snort rule file to FireEye CM.
        :param rules_file_path: {str} Rules filepath
        :return: raise FireEyeCMUnsuccessfulOperationError if failed to upload Snort rules file
                 raise Exception if failed to validate response
        """
        request_url = self._get_full_url("upload_custom_rules_file")
        files = [("filename", open(rules_file_path, "rb"))]
        self.session.headers.pop("Content-Type", None)
        response = self.session.post(request_url, files=files)

        # Check if response contains an error
        try:
            err_msg = response.json().get("fireeyeapis", {}).get("description")
            if err_msg:
                raise FireEyeCMUnsuccessfulOperationError(err_msg)
        except FireEyeCMUnsuccessfulOperationError:
            raise
        except Exception:
            pass

        validate_response(
            response,
            error_msg=f"Failed to upload custom Snort rules files from file path {rules_file_path}",
        )
