"""Unit tests for Google Cloud IAM Integration."""
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import json
import os
import pytest
import requests
from pytest_mock import MockerFixture

from google_cloud_iam.core.exceptions import (
    GoogleCloudIAMPolicyJSONError,
    GoogleCloudIAMRoleExistsError,
    GoogleCloudIAMRoleJSONError,
    GoogleCloudIAMRoleMissingError,
    GoogleCloudIAMServiceAccountExistsError,
    GoogleCloudIAMRoleIDInvalidError
)
from google_cloud_iam.core.GoogleCloudIAMManager import (
    GoogleCloudIAMManager
)


# CONSTANTS
ROLE_DEF = {"role":"data","role_dest":"data2"}
ROLE_ID = "role123xyz"
ROLE_VIEW = "Basic"
MAX_COUNT = 5
SHOW_DELETED = False
SERVICE_ACCOUNT_ID = "abcd-275007"
ETAG = "BwXDDgKFx7M="
SERVICE_ACCOUNT_EMAIL = "xys@abcd-275007.iam.gserviceaccount.com"
POLICY_JSON = {"abc":"xyz","def":"uvw"}

MOCK_DATA = json.load(
    open(
        os.path.join(os.path.dirname(__file__),
                       "mock_data.json")
    )
)

CREATE_PROJECT_ROLE = MOCK_DATA.get("create_project_role")
CREATE_PROJECT_ROLE_ERROR = MOCK_DATA.get("create_project_role_error")
CREATE_SERVICE_ACCOUNT = MOCK_DATA.get("create_service_account")
CREATE_SERVICE_ACCOUNT_ERROR = MOCK_DATA.get("create_service_account_error")
DELETE_PROJECT_ROLE = MOCK_DATA.get("delete_project_role")
GET_PROJECT_ROLE = MOCK_DATA.get("get_project_role")
GET_PROJECT_ROLE_DELETE = MOCK_DATA.get("get_project_role_error")
DELETE_SERVICE_ACCOUNT = MOCK_DATA.get("delete_service_account")
LIST_SERVICE_ACCOUNT = MOCK_DATA.get("list_service_account")
LIST_ROLES = MOCK_DATA.get("list_roles")
GET_SERVICE_ACCOUNT_IAM_POLICY = MOCK_DATA.get(
    "get_service_account_iam_policy"
)
SET_SERVICE_ACCOUNT_IAM_POLICY = MOCK_DATA.get(
    "set_service_account_iam_policy"
)
SET_SERVICE_ACCOUNT_IAM_POLICY_ERROR = MOCK_DATA.get(
    "set_service_account_iam_policy_error"
)
ERROR_JSON = CREATE_SERVICE_ACCOUNT_ERROR


@pytest.fixture
def google_cloud_iam_manager():
    """Returns Google Cloud IAM manager instance"""

    with open("config.json", "r") as f:
        data = f.read()

    config = json.loads(data)
    api_root = config['API Root']
    account_type = config["Account Type"]
    project_id = config["Project ID"]
    private_key_id = config["Private Key ID"]
    private_key = (
        rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        ).private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
    )
    client_email = config["Client Email"]
    client_id = config["Client ID"]
    auth_uri = config["Auth URI"]
    token_uri = config["Token URI"]
    auth_provider_x509_url = config["Auth Provider X509 URL"]
    client_x509_url = config["Client X509 URL"]
    service_account_json = config['Service Account Json File Content']
    workload_identity_email = config['Workload Identity Email']
    quota_project_id = config['Quota Project ID']

    manager = GoogleCloudIAMManager(
        api_root=api_root,
        account_type=account_type,
        project_id=project_id,
        private_key_id=private_key_id,
        private_key=private_key,
        client_email=client_email,
        client_id=client_id,
        auth_uri=auth_uri,
        token_uri=token_uri,
        auth_provider_x509_url=auth_provider_x509_url,
        client_x509_cert_url=client_x509_url,
        service_account_json=(
            json.dumps(service_account_json)
            if isinstance(service_account_json, dict)
            else service_account_json
        ),
        workload_identity_email=workload_identity_email,
        quota_project_id=quota_project_id
    )

    return manager


class TestGoogleCloudIAM:
    """Unit tests for Google Cloud IAM Integration."""

    def test_test_connectivity(
        self,
        mocker: MockerFixture,
        google_cloud_iam_manager: GoogleCloudIAMManager
    ) -> None:
        """Mocking test connectivity for the API.

        Args:
            mocker: The pytest-mock fixture used for mocking.
            google_cloud_iam_manager: Instance of GoogleCloudIAMManager class.

        Return:
            None
        """

        mock_get = mocker.Mock()
        mock_get.status_code = 200
        mocker.patch(
            'requests.Session.get',
            return_value=mock_get
        )
        google_cloud_iam_manager.test_connectivity()

    def test_test_connectivity_raise_manager_error_failure(
            self,
            mocker: MockerFixture,
            google_cloud_iam_manager: GoogleCloudIAMManager
        ) -> None:
        """Test for manager error for create_project_role method.

        Args:
            mocker: The pytest-mock fixture used for mocking.
            google_cloud_iam_manager: Instance of GoogleCloudIAMManager class.

        Return:
            None
        """

        mock_get = mocker.Mock()
        mock_get.json.return_value = CREATE_PROJECT_ROLE_ERROR
        mock_get.raise_for_status.side_effect = requests.HTTPError
        mock_get.status_code = 404

        mocker.patch(
            'requests.Session.get',
            return_value=mock_get
        )
        with pytest.raises(Exception) as error:
            google_cloud_iam_manager.test_connectivity()
        assert type(error.value).__name__ == 'GoogleCloudIAMManagerError'
        assert (
            "Failed to test connectivity with Google Cloud IAM:  custom_error"
            in str(error.value)
        )

    def test_create_project_role_valid_success(
        self,
        mocker: MockerFixture,
        google_cloud_iam_manager: GoogleCloudIAMManager
    ) -> None:
        """test create_project_role for API.

        Args:
            mocker: The pytest-mock fixture used for mocking.
            google_cloud_iam_manager: Instance of GoogleCloudIAMManager class.

        Return:
            None
        """

        mock_post = mocker.Mock()
        mock_post.json.return_value = CREATE_PROJECT_ROLE
        mock_post.status_code = 200
        mocker.patch(
            'requests.Session.post',
            return_value=mock_post
        )
        result = google_cloud_iam_manager.create_resource_role(
            role_id=ROLE_ID,
            role_definition_json=ROLE_DEF
        )

        actual_result = vars(result)["raw_data"]
        assert actual_result is CREATE_PROJECT_ROLE

    def test_create_project_role_raise_manager_error_failure(
        self,
        mocker: MockerFixture,
        google_cloud_iam_manager: GoogleCloudIAMManager
    ) -> None:
        """Test for manager error for create_project_role method.

        Args:
            mocker: The pytest-mock fixture used for mocking.
            google_cloud_iam_manager: Instance of GoogleCloudIAMManager class.

        Return:
            None
        """

        mock_post = mocker.Mock()
        mock_post.json.return_value = CREATE_PROJECT_ROLE_ERROR
        mock_post.raise_for_status.side_effect = requests.HTTPError
        mock_post.status_code = 404

        mocker.patch(
            'requests.Session.post',
            return_value=mock_post
        )
        with pytest.raises(Exception) as error:
            google_cloud_iam_manager.create_resource_role(
                role_id=ROLE_ID,
                role_definition_json=ROLE_DEF
            )
        assert type(error.value).__name__ == 'GoogleCloudIAMManagerError'
        assert 'Failed to create role with id: role123xyz' in str(
                error.value
            )

    def test_create_project_role_raise_json_error_failure(
        self,
        mocker: MockerFixture,
        google_cloud_iam_manager: GoogleCloudIAMManager
    ) -> None:
        """Test for json error for create_project_role method.

        Args:
            mocker: The pytest-mock fixture used for mocking.
            google_cloud_iam_manager: Instance of GoogleCloudIAMManager class.

        Return:
            None
        """

        mock_post = mocker.Mock()
        mock_post.json.return_value = CREATE_PROJECT_ROLE_ERROR
        mock_post.raise_for_status.side_effect = GoogleCloudIAMRoleJSONError
        mock_post.status_code = 404

        mocker.patch(
            'requests.Session.post',
            return_value=mock_post
        )
        with pytest.raises(GoogleCloudIAMRoleJSONError) as error:
            google_cloud_iam_manager.create_resource_role(
                role_id = ROLE_ID,
                role_definition_json=ROLE_DEF
            )
        assert type(error.value).__name__ == "GoogleCloudIAMRoleJSONError"

    def test_create_project_role_raise_invalid_error_failure(
        self,
        mocker: MockerFixture,
        google_cloud_iam_manager: GoogleCloudIAMManager
    ) -> None:
        """Test for invalid error for create_project_role method.

        Args:
            mocker: The pytest-mock fixture used for mocking.
            google_cloud_iam_manager: Instance of GoogleCloudIAMManager class.

        Return:
            None
        """

        mock_post = mocker.Mock()
        mock_post.json.return_value = CREATE_PROJECT_ROLE_ERROR
        mock_post.raise_for_status.side_effect = (
            GoogleCloudIAMRoleIDInvalidError
        )
        mock_post.status_code = 404

        mocker.patch(
            'requests.Session.post',
            return_value=mock_post
        )
        with pytest.raises(GoogleCloudIAMRoleIDInvalidError) as error:
            google_cloud_iam_manager.create_resource_role(
                role_id=ROLE_ID,
                role_definition_json=ROLE_DEF
            )
        assert type(error.value).__name__ == 'GoogleCloudIAMRoleIDInvalidError'

    def test_create_project_role_raise_exists_error_failure(
        self,
        mocker: MockerFixture,
        google_cloud_iam_manager: GoogleCloudIAMManager
    ) -> None:
        """Test for exists error for create_project_role method.

        Args:
            mocker: The pytest-mock fixture used for mocking.
            google_cloud_iam_manager: Instance of GoogleCloudIAMManager class.

        Return:
            None
        """

        mock_post = mocker.Mock()
        mock_post.json.return_value = CREATE_PROJECT_ROLE_ERROR
        mock_post.raise_for_status.side_effect = (
            GoogleCloudIAMRoleExistsError
        )
        mock_post.status_code = 404

        mocker.patch(
            'requests.Session.post',
            return_value=mock_post
        )
        with pytest.raises(GoogleCloudIAMRoleExistsError) as error:
            google_cloud_iam_manager.create_resource_role(
                role_id=ROLE_ID,
                role_definition_json=ROLE_DEF
            )
        assert type(error.value).__name__ == 'GoogleCloudIAMRoleExistsError'

    def test_create_service_account(
        self,
        mocker: MockerFixture,
        google_cloud_iam_manager: GoogleCloudIAMManager
    ) -> None:
        """test create_service_account for API.

        Args:
            mocker: The pytest-mock fixture used for mocking.
            google_cloud_iam_manager: Instance of GoogleCloudIAMManager class.

        Return:
            None
        """

        mock_post = mocker.Mock()
        mock_post.json.return_value = CREATE_SERVICE_ACCOUNT
        mock_post.status_code = 200

        mocker.patch(
            'requests.Session.post',
            return_value=mock_post
        )
        result = google_cloud_iam_manager.create_service_account(
            account_id=SERVICE_ACCOUNT_ID
        )
        actual_result = vars(result)["raw_data"]
        assert actual_result is CREATE_SERVICE_ACCOUNT

    def test_create_service_account_raise_exists_error_failure(
        self,
        mocker: MockerFixture,
        google_cloud_iam_manager: GoogleCloudIAMManager
    ) -> None:
        """Test for exists error for create_service_account method.

        Args:
            mocker: The pytest-mock fixture used for mocking.
            google_cloud_iam_manager: Instance of GoogleCloudIAMManager class.

        Return:
            None
        """

        mock_post = mocker.Mock()
        mock_post.json.return_value = CREATE_SERVICE_ACCOUNT_ERROR
        mock_post.raise_for_status.side_effect = (
            GoogleCloudIAMServiceAccountExistsError
        )
        mock_post.status_code = 404

        mocker.patch(
            'requests.Session.post',
            return_value = mock_post
        )
        with pytest.raises(GoogleCloudIAMServiceAccountExistsError) as error:
            google_cloud_iam_manager.create_service_account(
                account_id = SERVICE_ACCOUNT_ID
            )
        assert type(error.value).__name__ == (
            'GoogleCloudIAMServiceAccountExistsError'
        )

    def test_create_service_account_raise_manager_error_failure(
        self,
        mocker: MockerFixture,
        google_cloud_iam_manager: GoogleCloudIAMManager
    ) -> None:
        """test create_service_account for manager error

        Args:
            mocker: The pytest-mock fixture used for mocking.
            google_cloud_iam_manager: Instance of GoogleCloudIAMManager class.

        Return:
            None
        """

        mock_post = mocker.Mock()
        mock_post.json.return_value = CREATE_SERVICE_ACCOUNT_ERROR
        mock_post.raise_for_status.side_effect = requests.HTTPError
        mock_post.status_code = 404

        mocker.patch(
            'requests.Session.post',
            return_value=mock_post
        )
        with pytest.raises(Exception) as error:
            google_cloud_iam_manager.create_service_account(
                account_id=SERVICE_ACCOUNT_ID
            )
        assert type(error.value).__name__ == 'GoogleCloudIAMManagerError'
        assert (
            'Failed to create service account with account id: abcd-275007'
            in str(error.value)
        )

    def test_delete_project_role(
        self,
        mocker: MockerFixture,
        google_cloud_iam_manager: GoogleCloudIAMManager
    ) -> None:
        """Test delete_project_role for API.

        Args:
            mocker: The pytest-mock fixture used for mocking.
            google_cloud_iam_manager: Instance of GoogleCloudIAMManager class.

        Return:
            None
        """

        mock_delete = mocker.Mock()
        mock_delete.json.return_value = DELETE_PROJECT_ROLE
        mock_delete.status_code = 202

        mocker.patch(
            'requests.Session.delete',
            return_value=mock_delete
        )
        result = google_cloud_iam_manager.delete_resource_role(
            role_id=ROLE_ID,
            etag=ETAG
        )
        actual_result = vars(result)["raw_data"]
        assert actual_result is DELETE_PROJECT_ROLE

    def test_delete_project_role_raise_manager_error_failure(
        self,
        mocker: MockerFixture,
        google_cloud_iam_manager: GoogleCloudIAMManager
    ) -> None:
        """test delete_project_role for manager error

        Args:
            mocker: The pytest-mock fixture used for mocking.
            google_cloud_iam_manager: Instance of GoogleCloudIAMManager class.

        Return:
            None
        """

        mock_delete = mocker.Mock()
        mock_delete.json.return_value = ERROR_JSON
        mock_delete.raise_for_status.side_effect = requests.HTTPError
        mock_delete.status_code = 404

        mocker.patch(
            'requests.Session.delete',
            return_value=mock_delete
        )
        with pytest.raises(Exception) as error:
            google_cloud_iam_manager.delete_resource_role(
                role_id=ROLE_ID,
                etag=ETAG
            )
        assert type(error.value).__name__ == 'GoogleCloudIAMManagerError'
        assert (
            'Failed to delete role with id: role123xyz'
            in str(error.value)
        )

    def test_get_project_role(
        self,
        mocker: MockerFixture,
        google_cloud_iam_manager: GoogleCloudIAMManager
    ) -> None:
        """Test get_project_role for API.

        Args:
            mocker: The pytest-mock fixture used for mocking.
            google_cloud_iam_manager: Instance of GoogleCloudIAMManager class.

        Return:
            None
        """

        mock_get = mocker.Mock()
        mock_get.json.return_value = GET_PROJECT_ROLE
        mock_get.status_code = 200

        mocker.patch(
            'requests.Session.get',
            return_value=mock_get
        )
        result = google_cloud_iam_manager.get_resource_role(
            role_id=ROLE_ID
        )
        actual_result = vars(result)["raw_data"]
        assert actual_result is GET_PROJECT_ROLE

    def test_get_project_role_raise_missing_error_failure(
        self,
        mocker: MockerFixture,
        google_cloud_iam_manager: GoogleCloudIAMManager
    ) -> None:
        """Test for missing error for get_project_role method.

        Args:
            mocker: The pytest-mock fixture used for mocking.
            google_cloud_iam_manager: Instance of GoogleCloudIAMManager class.

        Return:
            None
        """

        mock_get = mocker.Mock()
        mock_get.json.return_value = GET_PROJECT_ROLE_DELETE
        mock_get.status_code = 404
        mock_get.raise_for_status.side_effect = GoogleCloudIAMRoleMissingError

        mocker.patch(
            'requests.Session.get',
            return_value=mock_get
        )
        with pytest.raises(GoogleCloudIAMRoleMissingError) as error:
            google_cloud_iam_manager.get_resource_role(
                role_id=ROLE_ID
            )
        assert type(error.value).__name__ == 'GoogleCloudIAMRoleMissingError'

    def test_delete_service_account(
        self,
        mocker: MockerFixture,
        google_cloud_iam_manager: GoogleCloudIAMManager
    ) -> None:
        """Test delete_project_role for API.

        Args:
            mocker: The pytest-mock fixture used for mocking.
            google_cloud_iam_manager: Instance of GoogleCloudIAMManager class.

        Return:
            None
        """

        mock_delete = mocker.Mock()
        mock_delete.json.return_value = DELETE_SERVICE_ACCOUNT
        mock_delete.status_code = 202

        mocker.patch(
            'requests.Session.delete',
            return_value=mock_delete
        )
        # delete_service_account does not return anything
        google_cloud_iam_manager.delete_service_account(
            service_account_email= SERVICE_ACCOUNT_EMAIL
        )

    def test_delete_service_account_raise_manager_error_failure(
        self,
        mocker: MockerFixture,
        google_cloud_iam_manager: GoogleCloudIAMManager
    ) -> None:
        """test delete_service_account for manager error

        Args:
            mocker: The pytest-mock fixture used for mocking.
            google_cloud_iam_manager: Instance of GoogleCloudIAMManager class.

        Return:
            None
        """

        mock_delete = mocker.Mock()
        mock_delete.json.return_value = ERROR_JSON
        mock_delete.raise_for_status.side_effect = requests.HTTPError
        mock_delete.status_code = 404

        mocker.patch(
            'requests.Session.delete',
            return_value=mock_delete
        )
        with pytest.raises(Exception) as error:
            google_cloud_iam_manager.delete_service_account(
                service_account_email=SERVICE_ACCOUNT_EMAIL
            )
        assert type(error.value).__name__ == 'GoogleCloudIAMManagerError'
        assert (
            'Failed to delete service account: xys@abcd-275007.iam.gservice'
            'account.com'
            in str(error.value)
            )

    def test_disable_service_account(
        self,
        mocker: MockerFixture,
        google_cloud_iam_manager: GoogleCloudIAMManager
    ) -> None:
        """Test disable_project_role for API.

        Args:
            mocker: The pytest-mock fixture used for mocking.
            google_cloud_iam_manager: Instance of GoogleCloudIAMManager class.

        Return:
            None
        """

        mock_post = mocker.Mock()
        mock_post.status_code = 200

        mocker.patch(
            'requests.Session.post',
            return_value=mock_post
        )
        # disable_service_account does not anything
        google_cloud_iam_manager.disable_service_account(
            service_account_email=SERVICE_ACCOUNT_EMAIL
        )

    def test_disable_service_account_raise_manager_error_failure(
        self,
        mocker: MockerFixture,
        google_cloud_iam_manager: GoogleCloudIAMManager
    ) -> None:
        """test disable_service_account for manager error

        Args:
            mocker: The pytest-mock fixture used for mocking.
            google_cloud_iam_manager: Instance of GoogleCloudIAMManager class.

        Return:
            None
        """

        mock_post = mocker.Mock()
        mock_post.json.return_value = ERROR_JSON
        mock_post.raise_for_status.side_effect = requests.HTTPError
        mock_post.status_code = 404

        mocker.patch(
            'requests.Session.post',
            return_value=mock_post
        )
        with pytest.raises(Exception) as error:
            google_cloud_iam_manager.disable_service_account(
                service_account_email=SERVICE_ACCOUNT_EMAIL
            )
        assert type(error.value).__name__ == 'GoogleCloudIAMManagerError'
        assert (
            'Failed to disable account: xys@abcd-275007.iam.gservice'
            'account.com'
            in str(error.value)
            )

    def test_enable_service_account(
        self,
        mocker: MockerFixture,
        google_cloud_iam_manager: GoogleCloudIAMManager
    ) -> None:
        """Test enable_project_role for API.

        Args:
            mocker: The pytest-mock fixture used for mocking.
            google_cloud_iam_manager: Instance of GoogleCloudIAMManager class.

        Return:
            None
        """

        mock_post = mocker.Mock()
        mock_post.status_code = 200

        mocker.patch(
            'requests.Session.post',
            return_value=mock_post
        )
        # enable_service_account does not anything
        google_cloud_iam_manager.enable_service_account(
            service_account_email= SERVICE_ACCOUNT_EMAIL
        )

    def test_enable_service_account_raise_manager_error_failure(
        self,
        mocker: MockerFixture,
        google_cloud_iam_manager: GoogleCloudIAMManager
    ) -> None:
        """test enable_service_account for manager error

        Args:
            mocker: The pytest-mock fixture used for mocking.
            google_cloud_iam_manager: Instance of GoogleCloudIAMManager class.

        Return:
            None
        """

        mock_post = mocker.Mock()
        mock_post.json.return_value = ERROR_JSON
        mock_post.raise_for_status.side_effect = requests.HTTPError
        mock_post.status_code = 404

        mocker.patch(
            'requests.Session.post',
            return_value=mock_post
        )
        with pytest.raises(Exception) as error:
            google_cloud_iam_manager.enable_service_account(
                service_account_email= SERVICE_ACCOUNT_EMAIL
            )
        assert type(error.value).__name__ == 'GoogleCloudIAMManagerError'
        assert (
            'Failed to enable account: xys@abcd-275007.iam.gservice'
            'account.com'
            in str(error.value)
            )

    def test_list_service_account(
        self,
        mocker: MockerFixture,
        google_cloud_iam_manager: GoogleCloudIAMManager
    ) -> None:
        """Test list_project_role for API.

        Args:
            mocker: The pytest-mock fixture used for mocking.
            google_cloud_iam_manager: Instance of GoogleCloudIAMManager class.

        Return:
            None
        """

        mock_get = mocker.Mock()
        mock_get.json.return_value = LIST_SERVICE_ACCOUNT
        mock_get.status_code = 200

        mocker.patch(
            'requests.Session.get',
            return_value=mock_get
        )
        result = google_cloud_iam_manager.list_service_accounts(
            max_results=MAX_COUNT
        )
        modified_result = vars(result[0])["raw_data"]
        excepted_result = LIST_SERVICE_ACCOUNT["accounts"][0]
        assert modified_result is excepted_result

    def test_list_service_account_raise_manager_error_failure(
        self,
        mocker: MockerFixture,
        google_cloud_iam_manager: GoogleCloudIAMManager
    ) -> None:
        """test list_service_account for manager error

        Args:
            mocker: The pytest-mock fixture used for mocking.
            google_cloud_iam_manager: Instance of GoogleCloudIAMManager class.

        Return:
            None
        """

        mock_get = mocker.Mock()
        mock_get.json.return_value = ERROR_JSON
        mock_get.raise_for_status.side_effect = requests.HTTPError
        mock_get.status_code = 404

        mocker.patch(
            'requests.Session.get',
            return_value=mock_get
        )
        with pytest.raises(Exception) as error:
            google_cloud_iam_manager.list_service_accounts(
                max_results=MAX_COUNT
            )
        assert type(error.value).__name__ == 'GoogleCloudIAMManagerError'
        assert (
            'Failed to list service accounts'
            in str(error.value)
            )

    def test_get_service_account_iam_policy(
        self,
        mocker: MockerFixture,
        google_cloud_iam_manager: GoogleCloudIAMManager
    ) -> None:
        """Test get_service_account_iam_policy for API.

        Args:
            mocker: The pytest-mock fixture used for mocking.
            google_cloud_iam_manager: Instance of GoogleCloudIAMManager class.

        Return:
            None
        """

        mock_post = mocker.Mock()
        mock_post.json.return_value = GET_SERVICE_ACCOUNT_IAM_POLICY
        mock_post.status_code = 200

        mocker.patch(
            'requests.Session.post',
            return_value=mock_post
        )
        result = google_cloud_iam_manager.get_service_account_iam_policy(
            service_account_email=SERVICE_ACCOUNT_EMAIL
        )
        modified_output = vars(result)["raw_data"]
        assert modified_output is GET_SERVICE_ACCOUNT_IAM_POLICY

    def test_get_service_account_iam_policy_raise_manager_error_failure(
        self,
        mocker: MockerFixture,
        google_cloud_iam_manager: GoogleCloudIAMManager
    ) -> None:
        """test test_get_service_account_iam_policy for manager error

        Args:
            mocker: The pytest-mock fixture used for mocking.
            google_cloud_iam_manager: Instance of GoogleCloudIAMManager class.

        Return:
            None
        """

        mock_post = mocker.Mock()
        mock_post.json.return_value = ERROR_JSON
        mock_post.raise_for_status.side_effect = requests.HTTPError
        mock_post.status_code = 404

        mocker.patch(
            'requests.Session.post',
            return_value=mock_post
        )
        with pytest.raises(Exception) as error:
            google_cloud_iam_manager.get_service_account_iam_policy(
                service_account_email = SERVICE_ACCOUNT_EMAIL
            )
        assert type(error.value).__name__ == 'GoogleCloudIAMManagerError'
        assert (
            'Failed to get service account IAM policy for account: '
            'xys@abcd-275007.iam.gserviceaccount.com'
            in str(error.value)
            )

    def test_list_project_roles(
        self,
        mocker: MockerFixture,
        google_cloud_iam_manager: GoogleCloudIAMManager
    ) -> None:
        """Test list_project_roles for API.

        Args:
            mocker: The pytest-mock fixture used for mocking.
            google_cloud_iam_manager: Instance of GoogleCloudIAMManager class.

        Return:
            None
        """

        mock_get = mocker.Mock()
        mock_get.json.return_value = LIST_ROLES
        mock_get.status_code = 200

        mocker.patch(
            'requests.Session.get',
            return_value=mock_get
        )
        result = google_cloud_iam_manager.list_resource_roles(
            show_deleted=SHOW_DELETED,
            role_view=ROLE_VIEW,
            max_results=MAX_COUNT
        )
        modified_result = vars(result[0])["raw_data"]
        expected_result = LIST_ROLES["roles"][0]
        assert modified_result is expected_result

    def test_list_project_roles_raise_manager_error_failure(
        self,
        mocker: MockerFixture,
        google_cloud_iam_manager: GoogleCloudIAMManager
    ) -> None:
        """test list_project_roles for manager error.

        Args:
            mocker: The pytest-mock fixture used for mocking.
            google_cloud_iam_manager: Instance of GoogleCloudIAMManager class.

        Return:
            None
        """

        mock_get = mocker.Mock()
        mock_get.json.return_value = ERROR_JSON
        mock_get.raise_for_status.side_effect = requests.HTTPError
        mock_get.status_code = 404

        mocker.patch(
            'requests.Session.get',
            return_value=mock_get
        )
        with pytest.raises(Exception) as error:
            google_cloud_iam_manager.list_resource_roles(
                show_deleted=SHOW_DELETED,
                role_view=ROLE_VIEW,
                max_results=MAX_COUNT
            )
        assert type(error.value).__name__ == 'GoogleCloudIAMManagerError'
        assert (
            'Failed to list roles'
            in str(error.value)
            )

    def test_list_roles(
        self,
        mocker: MockerFixture,
        google_cloud_iam_manager: GoogleCloudIAMManager
    ) -> None:
        """Test test_list_roles for API.

        Args:
            mocker: The pytest-mock fixture used for mocking.
            google_cloud_iam_manager: Instance of GoogleCloudIAMManager class.

        Return:
            None
        """

        mock_get = mocker.Mock()
        mock_get.json.return_value = LIST_ROLES
        mock_get.status_code = 200

        mocker.patch(
            'requests.Session.get',
            return_value=mock_get
        )
        result = google_cloud_iam_manager.list_roles(
            show_deleted=SHOW_DELETED,
            role_view=ROLE_VIEW,
            max_results=MAX_COUNT
        )
        modified_result = vars(result[0])["raw_data"]
        expected_result = LIST_ROLES["roles"][0]
        assert modified_result is expected_result

    def test_list_roles_raise_manager_error_failure(
        self,
        mocker: MockerFixture,
        google_cloud_iam_manager: GoogleCloudIAMManager
    ) -> None:
        """test list_roles for manager error.

        Args:
            mocker: The pytest-mock fixture used for mocking.
            google_cloud_iam_manager: Instance of GoogleCloudIAMManager class.

        Return:
            None
        """

        mock_get = mocker.Mock()
        mock_get.json.return_value = ERROR_JSON
        mock_get.raise_for_status.side_effect = requests.HTTPError
        mock_get.status_code = 404

        mocker.patch(
            'requests.Session.get',
            return_value=mock_get
        )
        with pytest.raises(Exception) as error:
            google_cloud_iam_manager.list_roles(
                show_deleted=SHOW_DELETED,
                role_view=ROLE_VIEW,
                max_results=MAX_COUNT
            )
        assert type(error.value).__name__ == 'GoogleCloudIAMManagerError'
        assert (
            'Failed to list roles'
            in str(error.value)
            )

    def test_set_service_account_iam_policy(
        self,
        mocker: MockerFixture,
        google_cloud_iam_manager: GoogleCloudIAMManager
    ) -> None:

        """Test set_service_account_iam_policy for API.

        Args:
            mocker: The pytest-mock fixture used for mocking.
            google_cloud_iam_manager: Instance of GoogleCloudIAMManager class.

        Return:
            None
        """

        mock_post = mocker.Mock()
        mock_post.json.return_value = SET_SERVICE_ACCOUNT_IAM_POLICY
        mock_post.status_code = 200

        mocker.patch(
            'requests.Session.post',
            return_value=mock_post
        )
        result = google_cloud_iam_manager.set_service_account_iam_policy(
            service_account_email=SERVICE_ACCOUNT_EMAIL,
            policy_json=POLICY_JSON
        )
        modified_output = vars(result)["raw_data"]
        assert modified_output is SET_SERVICE_ACCOUNT_IAM_POLICY

    def test_set_service_account_iam_policy_raise_manager_error_failure(
        self,
        mocker: MockerFixture,
        google_cloud_iam_manager: GoogleCloudIAMManager
    ) -> None:

        """test set_service_account_iam_policy for manager error.

        Args:
            mocker: The pytest-mock fixture used for mocking.
            google_cloud_iam_manager: Instance of GoogleCloudIAMManager class.

        Return:
            None
        """

        mock_post = mocker.Mock()
        mock_post.json.return_value = ERROR_JSON
        mock_post.raise_for_status.side_effect = requests.HTTPError
        mock_post.status_code = 404

        mocker.patch(
            'requests.Session.post',
            return_value=mock_post
        )
        with pytest.raises(Exception) as error:
            google_cloud_iam_manager.set_service_account_iam_policy(
                service_account_email=SERVICE_ACCOUNT_EMAIL,
                policy_json=POLICY_JSON
            )
        assert type(error.value).__name__ == 'GoogleCloudIAMManagerError'
        assert (
            'Failed to set IAM policy for account: '
            'xys@abcd-275007.iam.gserviceaccount.com'
            in str(error.value)
            )

    def test_set_service_account_iam_policy_raise_json_error_failure(
        self,
        mocker: MockerFixture,
        google_cloud_iam_manager: GoogleCloudIAMManager
    ) -> None:

        """Test for JSON error for set_service_account_iam_policy method.

        Args:
            mocker: The pytest-mock fixture used for mocking.
            google_cloud_iam_manager: Instance of GoogleCloudIAMManager class.

        Return:
            None
        """

        mock_post = mocker.Mock()
        mock_post.json.return_value = SET_SERVICE_ACCOUNT_IAM_POLICY_ERROR
        mock_post.raise_for_status.side_effect = GoogleCloudIAMPolicyJSONError
        mock_post.status_code = 404

        mocker.patch(
            'requests.Session.post',
            return_value=mock_post
        )
        with pytest.raises(GoogleCloudIAMPolicyJSONError) as error:
            google_cloud_iam_manager.set_service_account_iam_policy(
                service_account_email=SERVICE_ACCOUNT_EMAIL,
                policy_json=POLICY_JSON
            )
        assert type(error.value).__name__ == 'GoogleCloudIAMPolicyJSONError'
