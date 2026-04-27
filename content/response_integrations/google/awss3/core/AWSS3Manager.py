from __future__ import annotations
import json
import os
import re

import boto3

from .AWSS3Parser import AWSS3Parser
from .consts import REGEX_BUCKET_PATH
from .exceptions import AWSS3StatusCodeException, AWSS3PathException


class AWSS3Manager:
    """
    AWS S3 Manager
    """

    VALID_STATUS_CODES = (200, 204)

    def __init__(self, aws_access_key, aws_secret_key, aws_default_region):
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key
        self.aws_default_region = aws_default_region

        session = boto3.session.Session()

        self.s3_client = session.client(
            "s3",
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_default_region,
        )

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate client s3 response status code
        :param response: client s3 response
        :return: raise AWSS3StatusCodeException if status code is not valid
        """
        if (
            response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            not in AWSS3Manager.VALID_STATUS_CODES
        ):
            raise AWSS3StatusCodeException(f"{error_msg}. Response: {response}")

    def test_connectivity(self):
        """
        Test connectivity with AWS S3 service by calling the list_buckets method
        :return:
                raise boto3.exception.ClientError if connectivity failed
                raise AWSS3StatusCodeException if connectivity failed to validate status code
        """
        # This is a temporary solution for connectivity testing approved by product. List buckets function is
        # not limited and can cause a problem with large number of buckets.
        # PR: https://github.com/Siemplify/SiemplifyMarketPlace/pull/913
        response = self.s3_client.list_buckets()
        self.validate_response(
            response, error_msg="Failed to test connectivity with AWS S3 Service."
        )

    def get_list_buckets(self):
        """
        Get list of AWS S3 buckets.
        :return: tuple with Owner data model and list of Buckets data models
            raise boto3.exception.ClientError if client failed to list buckets
            raise AWSS3StatusCodeException if client failed to get list of buckets
        """
        response = self.s3_client.list_buckets()
        self.validate_response(response, error_msg="Failed to fetch list of buckets.")

        owner = AWSS3Parser.build_owner(response["Owner"])
        buckets = []

        for json_bucket in response["Buckets"]:
            buckets.append(AWSS3Parser.build_bucket(json_bucket))

        return (owner, buckets)

    def get_bucket_policy(self, bucket_name):
        """
        Get S3 bucket policy.
        :param bucket_name:
        :return: Policy data model
            raise boto3.exception.ClientError if client failed to get bucket policy
            raise AWSS3StatusCodeException if getting bucket policy failed to validate status code
        """
        response = self.s3_client.get_bucket_policy(Bucket=bucket_name.lower())
        self.validate_response(
            response,
            error_msg=f"Failed to get bucket policy for bucket {bucket_name.lower()}",
        )

        policy_json = json.loads(response.get("Policy"))
        policy = AWSS3Parser.build_bucket_policy(policy_json)
        return policy

    def set_bucket_policy(self, bucket_name, bucket_policy):
        """
        Set S3 bucket policy.
        :param bucket_name: {str} bucket name
        :param bucket_policy:  {str} string type json of bucket policy. Example: https://docs.aws.amazon.com/AmazonS3/latest/dev/example-bucket-policies.html
        :return: raise boto3.exception.ClientError if setting bucket policy failed
                 raise AWSS3StatusCodeException if setting bucket policy failed to validate status code
        """
        response = self.s3_client.put_bucket_policy(
            Bucket=bucket_name.lower(), Policy=bucket_policy
        )
        self.validate_response(
            response,
            error_msg=(
                f"Failed to set bucket policy: {bucket_policy} for bucket: "
                f"{bucket_name}"
            ),
        )

    def list_bucket_objects(self, bucket_name, max_objects_to_return=50):
        """
        Get list of bucket contents
        :param bucket_name: {str} bucket name
        :param max_objects_to_return: {int} how many objects to return
        :return: list of Content data models
                raise boto3.exception.ClientError if client failed to list bucket objects
                raise AWSS3StatusCodeException if getting bucket objects failed to validate status code
        """
        bucket_contents_response = self.s3_client.list_objects(
            Bucket=bucket_name.lower(), MaxKeys=max_objects_to_return
        )
        self.validate_response(
            bucket_contents_response,
            error_msg=f"Failed to get bucket objects for {bucket_name}",
        )
        contents = []
        for bucket_content in bucket_contents_response["Contents"]:
            contents.append(AWSS3Parser.build_bucket_content(bucket_content))
        return contents

    @staticmethod
    def parse_bucket_file_path(bucket_file_path):
        """
        Parse bucket file path to bucket name and filename (e.g s3://testsiemplify/test/test.txt)
        :param bucket_file_path: {str} bucket file path
        :return: tuple of {str} bucket name and {str} filename
                raise AWSS3PathException if failed to parse bucket file path
        """
        s3_bucket_path_match = re.match(REGEX_BUCKET_PATH, bucket_file_path)
        if not s3_bucket_path_match:
            raise AWSS3PathException(
                f"Failed to parse bucket file path {bucket_file_path}"
            )

        return s3_bucket_path_match.group(1), s3_bucket_path_match.group(2)

    @staticmethod
    def validate_download_path(download_file_path):
        """
        Validate download file path
        :param download_file_path: {str} of FILE in local path
        :return: raise AWSS3PathException if failed to validate download path
        """
        if os.path.exists(download_file_path):
            raise AWSS3PathException(
                "File with that download path already exists or not accessible due to "
                "restricted permissions."
            )

        if os.path.exists(download_file_path) and not os.path.isfile(
            download_file_path
        ):
            raise AWSS3PathException("Download path must be a file.")

    @staticmethod
    def validate_upload_path(upload_file_path):
        """
        Validate upload file path
        :param upload_file_path: {str} of file to upload to AWS S3 bucket
        :return: raise AWSS3PathException if failed to validate upload file path
        """
        if not os.path.exists(upload_file_path):
            raise AWSS3PathException(
                "File with that upload path does not exist or not accessible due to "
                "restricted permissions."
            )

        if not os.path.isfile(upload_file_path):
            raise AWSS3PathException("Upload path must be a file.")

    def download_file(self, bucket_file_path, download_file_path):
        """
        Download file from AWS S3 bucket to download path
        :param bucket_file_path: {str} S3 bucket path from which to download file from
        :param download_file_path: {str} download file path
        :return: raise AWSS3PathException if failed to parse bucket file path according to bucket file path format or failed to
                                  validate download path
                 raise boto3.exception.ClientError if failed to validate download path
        """
        bucket_name, filename = self.parse_bucket_file_path(bucket_file_path)

        self.validate_download_path(download_file_path)
        self.s3_client.download_file(bucket_name, filename, download_file_path)

    def upload_file(self, bucket_file_path, upload_file_path):
        """
        Upload file to AWS S3 bucket
        :param bucket_file_path: {str} S3 bucket path to which to upload to
        :param upload_file_path: {str} upload file path
        :return: raise AWSS3PathException if failed to parse bucket file path according to bucket file path format
                 raise boto3.exception.ClientError if failed to validate upload file path
        """
        bucket_name, filename = self.parse_bucket_file_path(bucket_file_path)

        self.validate_upload_path(upload_file_path)
        self.s3_client.upload_file(upload_file_path, bucket_name, filename)
