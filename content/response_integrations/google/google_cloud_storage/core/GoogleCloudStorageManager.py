from __future__ import annotations
import json
import os

import requests
import requests.adapters
from google.auth.exceptions import TransportError, RefreshError
from google.cloud import storage
from google.auth.transport.requests import AuthorizedSession, Request


from soar_sdk.SiemplifyLogger import SiemplifyLogger
from TIPCommon.types import SingleJson
from TIPCommon.rest.auth import build_credentials_from_sa
from TIPCommon.rest.gcp import get_workload_sa_email, retrieve_project_id
from TIPCommon.utils import is_empty_string_or_none
from . import consts
from .GoogleCloudStorageParser import GoogleCloudStorageParser
from .exceptions import (
    GoogleCloudStorageBadRequestError,
    GoogleCloudStorageNotFoundError,
    GoogleCloudStorageForbiddenError,
    GoogleCloudStorageNoConnectionsError,
    GoogleCloudStorageManagerError,
)


class GoogleCloudStorageManager:
    """
    Google Cloud Storage Manager
    """

    def __init__(
        self,
        service_account: SingleJson,
        workload_identity_email: str,
        logger: SiemplifyLogger,
        api_root: str = "",
        project_id: str = "",
        quota_project_id="",
        verify_ssl: bool = True,
    ):
        self.service_account = service_account
        self.workload_identity_email = workload_identity_email
        self.api_root = api_root
        self.quota_project_id = quota_project_id
        self.verify_ssl = verify_ssl
        self.logger = logger
        self.parser = GoogleCloudStorageParser()
        self.client = None

        self.project_id = (
            project_id
            if not is_empty_string_or_none(project_id)
            else retrieve_project_id(self.service_account, workload_identity_email)
        )

        self._prepare_http_client()

    def _prepare_http_client(self):
        """Prepare http client"""
        try:
            credentials = build_credentials_from_sa(
                user_service_account=self.service_account,
                quota_project_id=self.quota_project_id,
                target_principal=self.workload_identity_email,
                scopes=consts.SCOPE,
                verify_ssl=self.verify_ssl,
            )
        except RefreshError as e:
            workload_sa = get_workload_sa_email("Principal Could not be found")

            raise GoogleCloudStorageManagerError(
                "Impersonation is not allowed for the provided service "
                f"account {self.workload_identity_email}! In Order to use Workload "
                f'Identity Email, Add the "Service Account Token Creator" IAM Role to '
                f"{workload_sa} on the desired Service Account"
            ) from e

        try:
            session = AuthorizedSession(
                credentials, auth_request=self.prepare_auth_request(self.verify_ssl)
            )
            session.verify = self.verify_ssl
            self.client = storage.Client(
                project=self.project_id,
                credentials=credentials,
                _http=session,
                client_options={"api_endpoint": self.api_root}
            )
        except ValueError as error:
            raise GoogleCloudStorageManagerError(f"Wrong Credentials: {error}")

    @staticmethod
    def prepare_auth_request(verify_ssl: bool = True):
        """
        Prepare an authenticated request.

        Note: This method is a duplicate of the same method in the GoogleCloudComputeManager class. The only change is
        that created session is using verify_ssl parameter to allow self-signed certificates.
        """
        auth_request_session = requests.Session()
        auth_request_session.verify = verify_ssl

        # Using an adapter to make HTTP requests robust to network errors.
        # This adapter retries HTTP requests when network errors occur
        # and the requests seems safely retryable.
        retry_adapter = requests.adapters.HTTPAdapter(max_retries=3)
        auth_request_session.mount("https://", retry_adapter)

        # Do not pass `self` as the session here, as it can lead to
        # infinite recursion.
        return Request(auth_request_session)

    @staticmethod
    def validate_error(response, error_msg="An error occurred"):
        try:
            if type(response) == TransportError:
                raise TransportError("No internet connection")

            response = response.response
            if response.status_code == consts.NOT_FOUND:
                try:
                    error_message = json.loads(response.content).get("error")
                    raise GoogleCloudStorageNotFoundError(
                        error_message.get("message", "Not Found")
                    )
                except json.decoder.JSONDecodeError as error:
                    raise GoogleCloudStorageNotFoundError(response.text)

            if response.status_code == consts.FORBIDDEN:
                error_message = json.loads(response.content).get("error")
                raise GoogleCloudStorageForbiddenError(
                    error_message.get("message", "Forbidden")
                )

            else:
                error_message = json.loads(response.content).get("error")
                raise GoogleCloudStorageBadRequestError(
                    f"{error_msg}: {error_message.get('message', 'Bad Request')}"
                )

        except (
            GoogleCloudStorageBadRequestError,
            GoogleCloudStorageForbiddenError,
            GoogleCloudStorageNotFoundError,
        ):
            raise

        except TransportError as error:
            raise GoogleCloudStorageNoConnectionsError(error)

        except Exception as error:
            raise GoogleCloudStorageManagerError("Wrong Credentials")

    def test_connectivity(self):
        """
        Test Connectivity
        """
        try:
            list(self.client.list_buckets(max_results=1))
            return True
        except Exception as error:
            raise GoogleCloudStorageManagerError(f"{error}")

    def list_buckets(self, max_results=consts.DEFAULT_PAGE_SIZE):
        """
        Retrieve a list of buckets from Google Cloud Storage.
        param max_results: Max number of results to return
        return: [{datamodels.Bucket}] List of Buckets models
        """
        response = self.client.list_buckets(max_results=max_results)
        buckets = []

        try:
            for page in response.pages:
                if len(buckets) >= max_results:
                    break
                buckets.extend(self.parser.build_buckets_obj(page.raw_page))

            return buckets[:max_results]

        except Exception as error:
            self.validate_error(error, "Unable to list buckets")

    def get_acl(self, bucket_name):
        """
        Retrieve the access control list (ACL) for a Cloud Storage bucket.
        :param bucket_name: {str} The name of the bucket to fetch his ACLs
        :return: [{datamodels.ACL}] List of ACLs models
        """
        try:
            response = self.client.get_bucket(bucket_or_name=bucket_name)
            return self.parser.build_acl_obj(response)
        except Exception as error:
            self.validate_error(error, "Unable to list buckets")

    def list_buckets_objects(
        self,
        bucket_name,
        max_objects_to_return=consts.DEFAULT_PAGE_SIZE,
        retrieve_acl=True,
    ):
        """
        List bucket objects in Google Cloud storage.
        :param bucket_name: {str} bucket name to retrieve objects from
        :param max_objects_to_return:  {int} max number of objects to return
        :param retrieve_acl: {bool} True if to try and retrieve an ACL. Buckets of type uniform will raise and exception if
        retrieve_acl=True.
        :return: {[datamodel.BucketObject]} List of bucket objects
        """
        response = self.client.list_blobs(
            bucket_name, max_results=max_objects_to_return
        )
        bucket_objects = []

        try:
            for page in response.pages:
                if len(bucket_objects) >= max_objects_to_return:
                    break

                for blob in page:
                    bucket_objects.append(
                        self.parser.build_bucket_object_obj(blob, retrieve_acl)
                    )
            return bucket_objects
        except Exception as error:
            self.validate_error(error, "Unable to list bucket objects")

    def update_acl(self, acl):
        """
        Update ACL of a bucket in Google Cloud Storage
        :param acl: {datamodels.ACL} ACL data model object
        :return: True if there is no errors
        """
        try:
            #  acl.save is an API call from Google Cloud Storage
            response = acl.save()
            return True
        except Exception as error:
            self.validate_error(error, "Unable to update acl permission")

    def get_bucket(self, bucket_name):
        """
        Get bucket from Google Cloud Storage
        :param bucket_name: {str} The name of the bucket
        :return: {datamodels.Bucket} Bucket Data Model
        """
        try:
            response = self.client.get_bucket(bucket_or_name=bucket_name)
            return self.parser.build_bucket_from_google_obj(response)
        except Exception as error:
            self.validate_error(error, "Unable to find bucket")

    def get_blob(self, object_name):
        """
        Google Cloud Storage API call that return the object if exits
        :param object_name: The name of the object to retrieve.
        :return: {Blob} Google Cloud Storage Blob object
        """
        return object_name.get_blob(object_name)

    def upload_file(self, file_object, upload_path):
        """
        Upload file to Cloud Storage bucket.
        :param file_object: {GoogleCloudStorage.Blob} Google Cloud Storage file object
        :param upload_path: {str} The path specified where to upload the file from
        :return: raise Exception if failed to upload file
        """
        try:
            file_object.upload_from_filename(upload_path)
        except Exception as error:
            self.validate_error(error, error_msg=f"Unable to upload file {upload_path}")

    def download_file(self, file_object, download_path):
        """
        Download an object from a Cloud Storage bucket.
        :param file_object: {GoogleCloudStorage.Blob} Google Cloud Storage file object
        :param download_path: {str} The path specified to where to download the file
        :return: True if the file was downloaded successfully
        """
        try:
            if not os.path.exists(os.path.dirname(download_path)):
                os.makedirs(os.path.dirname(download_path))

            with open(download_path, "wb") as file:
                self.client.download_blob_to_file(file_object, file)
            return True

        except (FileNotFoundError, PermissionError):
            raise

        except Exception as error:
            self.validate_error(error, "Unable to download the file")

    @staticmethod
    def remove_public_access(bucket: storage.Bucket) -> None:
        """
        Remove bucket public access by removing PUBLIC_ACCESS_PRINCIPALS principals
        from the bucket-level policy

        Args:
            bucket (storage.Bucket): bucket object to remove public access from
        """
        policy = bucket.get_iam_policy()

        for binding in policy.bindings:
            for principal in consts.PUBLIC_ACCESS_PRINCIPALS:
                if principal in binding.get("members"):
                    binding["members"].discard(principal)

        bucket.set_iam_policy(policy)

    @staticmethod
    def update_public_access_prevention(bucket: storage.Bucket, value: str) -> None:
        """Update bucket public access prevention

        Args:
            bucket (storage.Bucket): bucket to update public access prevention for
            value (str): value to set for public access prevention
        """
        bucket.iam_configuration.public_access_prevention = value
        bucket.patch()
