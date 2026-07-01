from __future__ import annotations

import datetime
import re
import pytest
from pytest_mock import MockerFixture
from TIPCommon.types import SingleJson
from SiemplifyConnectors import SiemplifyConnectorExecution
from core\
    .MicrosoftGraphMailDelegatedManager import ApiManager
from core import constants
from core.datamodels import (
    MicrosoftGraphEmail,
    MicrosoftGraphFolder,
)
from core.constants import TIME_FORMAT
from core.exceptions import (
    MicrosoftGraphMailManagerError,
)


class TestApiManager:
    """Unit tests for Integration's ApiManager methods."""

    @pytest.fixture(scope="function")
    def folder(
        self,
        ms_graph_mail_manager: ApiManager,
        mock_data: SingleJson,
    ) -> MicrosoftGraphFolder:
        """Get MicrosoftGraphFolder object.

        Args:
            ms_graph_mail_manager (_type_): ApiManager instance.
            mock_data (SingleJson): mock data for the unit tests.

        Yields:
            MicrosoftGraphFolder: MicrosoftGraphFolder object.
        """
        yield MicrosoftGraphFolder(
            mock_data.get(constants.DEFAULT_FOLDER_NAME),
            folder_id=mock_data.get(constants.DEFAULT_FOLDER_NAME).get("id"),
            display_name=constants.DEFAULT_FOLDER_NAME,
            mailbox_name=ms_graph_mail_manager.mail_address,
        )

    @pytest.mark.parametrize("folder_name", ["Inbox", "Sent", "Éléments envoyés"])
    def test_get_folder(
        self,
        mocker: MockerFixture,
        ms_graph_mail_manager: ApiManager,
        mock_data: SingleJson,
        folder_name: str,
    ) -> None:
        """Test to get folder datamodels.MicrosoftGraphFolder object.

        Args:
            mocker (MockerFixture): pytest-mock fixture.
            ms_graph_mail_manager (ApiManager): Manager object.
            mock_data (SingleJson): mock json data.
            folder_name (str): Folder name to fetch the details.
        """
        # Arrange
        mock_data = mock_data.get(folder_name)
        mock_get = mocker.Mock()
        mock_get.json.return_value = mock_data
        mocker.patch.object(
            ms_graph_mail_manager.session,
            "request",
            return_value=mock_get,
        )

        # Act
        folder = ms_graph_mail_manager.get_folder_by_name(folder_name)

        # Assert
        assert "MicrosoftGraphFolder" in type(folder).__name__
        assert folder.display_name == folder_name

    @pytest.mark.parametrize(
        (
            "folder_name, datetime_str, limit, unread_only, "
            "email_exclude_pattern, expected_emails_count"
        ),
        [
            ("Inbox", "2022-09-19T16:49:27Z", 20, False, "", 1),
            ("Inbox", "2022-09-19T16:49:27Z", 20, True, "", 1),
        ],
    )
    def test_get_emails(
        self,
        mocker: MockerFixture,
        ms_graph_mail_manager: ApiManager,
        class_mocker: MockerFixture,
        mock_data: SingleJson,
        folder_name: str,
        datetime_str: str,
        limit: int,
        unread_only: bool,
        email_exclude_pattern: str,
        expected_emails_count: int,
    ) -> None:
        """Test to get emails datamodels.MicrosoftGraphFolder object.

        Args:
            mocker (MockerFixture): MockerFixture fixture.
            ms_graph_mail_manager (ApiManager): ApiManager instance.
            class_mocker (MockerFixture): MockerFixture fixture.
            mock_data (SingleJson): mock json data.
            folder_name (str): Mail folder name.
            datetime_str (str): datetime string.
            limit (int): limit to get mails.
            unread_only (bool): True if need only unread emails otherwise False.
            email_exclude_pattern (str): Pattern to excluded the emails.
            expected_emails_count (int): expected email count to return.
        """
        # Arrange
        class_mocker.patch("test_manager.SiemplifyConnectorExecution")
        ms_graph_mail_manager.siemplify = SiemplifyConnectorExecution()
        existing_ids = []
        mock_data = mock_data.get("get_mails")
        mock_get = mocker.Mock()
        mock_get.json.return_value = mock_data
        mocker.patch.object(
            ms_graph_mail_manager.session,
            "request",
            return_value=mock_get,
        )

        # Act
        for _ in range(1):
            emails = ms_graph_mail_manager.get_emails(
                folder_name=folder_name,
                datetime_from=datetime.datetime.strptime(datetime_str, TIME_FORMAT),
                max_email_per_cycle=limit,
                existing_ids=existing_ids,
                unread_only=unread_only,
                email_exclude_pattern=email_exclude_pattern,
            )
            assert len(emails) == limit
            emails = [emails[0]]
            for email in emails:
                assert "MicrosoftGraphEmail" in type(email).__name__
                if email.has_attachments:
                    print(email.id)
                assert email.id not in existing_ids
                existing_ids.append(email.id)
                if unread_only:
                    assert not email.raw_data.get("isRead")
                if email_exclude_pattern:
                    assert not re.match(
                        re.compile(email_exclude_pattern), email.subject
                    )
                    assert not re.match(
                        re.compile(email_exclude_pattern), email.body.get("content")
                    )
        # Assert
        assert len(existing_ids) == expected_emails_count

    @pytest.mark.parametrize(
        "email_id",
        [
            "AAMkADU0MDJjNjJkLTc3MzAtNGM5My04ZjM0LTZiYzVjMDI4ZTZlNQBGAA"
            "AAAADLc0XF-C8kRJTduC5WOJE-BwDby9ZjVdTJTJRS8jxrcA_oAAAAAAEM"
            "AADby9ZjVdTJTJRS8jxrcA_oAALEE3T3AAA=",
            "AAMkADU0MDJjNjJkLTc3MzAtNGM5My04ZjM0LTZiYzVjMDI4ZTZlNQBGAA"
            "AAAADLc0XF-C8kRJTduC5WOJE-BwDby9ZjVdTJTJRS8jxrcA_oAAAAAAEM"
            "AADby9ZjVdTJTJRS8jxrcA_oAALEE3T5AAA=",
        ],
    )
    def test_get_attachments(
        self,
        mocker: MockerFixture,
        ms_graph_mail_manager: ApiManager,
        mock_data: SingleJson,
        folder: MicrosoftGraphFolder,
        email_id: str,
    ) -> None:
        """Test to get attachment datamodels.MicrosoftGraphFileAttachment object

        Args:
            mocker (MockerFixture): pytest-mock fixture.
            ms_graph_mail_manager (ApiManager): Manager object.
            mock_data (SingleJson): mock json data.
            folder (MicrosoftGraphFolder): Mail MicrosoftGraphFolder object fixture.
            email_id (str): email id string.
        """
        # Arrange
        mock_data_attachment = {"value": [mock_data.get("get_attachment")]}
        mock_get = mocker.Mock()
        mock_get.json.return_value = mock_data_attachment
        mocker.patch.object(ms_graph_mail_manager.session, "get", return_value=mock_get)
        attachments = ms_graph_mail_manager.load_attachments_for_email(
            folder_id=folder.id,
            email_id=email_id,
            mail_address=ms_graph_mail_manager.mail_address,
        )
        for attachment in attachments:
            assert "MicrosoftGraphFileAttachment" in type(attachment).__name__
            assert attachment.id
            assert attachment.size
            assert attachment.name
            if not attachment.is_to_large:
                # Assert
                assert ms_graph_mail_manager.load_attachment_content(
                    folder.id, email_id, attachment.id
                )
        assert len(attachments) > 0

    def test_get_mail_details_valid_success(
        self,
        mocker: MockerFixture,
        ms_graph_mail_manager: ApiManager,
        mock_data: SingleJson,
        folder: MicrosoftGraphFolder,
    ) -> None:
        """Test to get mail datamodels.MicrosoftGraphEmail object

        Args:
            mocker (MockerFixture): pytest-mock fixture.
            ms_graph_mail_manager (ApiManager): Manager object.
            mock_data (SingleJson): mock json data.
            folder (MicrosoftGraphFolder): Mail MicrosoftGraphFolder object fixture.
        """
        # Arrange
        email_id = (
            "AAMkADU0MDJjNjJkLTc3MzAtNGM5My04ZjM0LTZiYzVjMDI4ZTZlNQBGAAAAAADLc0"
            "XF-C8kRJTduC5WOJE-BwDby9ZjVdTJTJRS8jxrcA_oAALg_Vq3AADby9ZjVdTJTJRS"
            "8jxrcA_oAAP1qhPJAAA="
        )
        data = mock_data.get("get_mail_details")
        mock_get = mocker.Mock()
        mock_get.json.return_value = data
        mocker.patch.object(ms_graph_mail_manager.session, "get", return_value=mock_get)
        # Act
        email = ms_graph_mail_manager.get_mail_details(folder=folder, email_id=email_id)

        # Assert
        assert type(email).__name__ == "MicrosoftGraphEmail"
        assert email_id == email.id

    def test_get_mail_details_invalid_raise_exception(
        self,
        mocker: MockerFixture,
        ms_graph_mail_manager: ApiManager,
        folder: MicrosoftGraphFolder,
    ) -> None:
        """Test to raise exception in ApiManager.get_mail_details
        method.
        Args:
            mocker (MockerFixture): pytest-mock fixture.
            ms_graph_mail_manager (ApiManager): Manager object.
            folder (MicrosoftGraphFolder): Mail MicrosoftGraphFolder object fixture.
        """
        # Arrange
        email_id = (
            "AAMkADU0MDJjNjJkLTc3MzAtNGM5My04ZjM0LTZiYzVjMDI4ZTZlNQBGAAAAAADLc0"
            "XF-C8kRJTduC5WOJE-BwDby9ZjVdTJTJRS8jxrcA_oAALg_Vq3AADby9ZjVdTJTJRS"
            "8jxrcA_oAAP1qhPJAAA="
        )
        mock_get = mocker.Mock()
        mock_get.raise_for_status.side_effect = Exception("MessageId is malformed.")
        mocker.patch.object(ms_graph_mail_manager.session, "get", return_value=mock_get)

        # Act
        with pytest.raises(Exception) as error:
            ms_graph_mail_manager.get_mail_details(folder=folder, email_id=email_id)

        # Assert
        assert "MessageId is malformed." in str(error.value)

    def test_get_all_replies_valid_success(
        self,
        mocker: MockerFixture,
        ms_graph_mail_manager: ApiManager,
        mock_data: SingleJson,
    ) -> None:
        """Test to get list of MicrosoftGraphEmail object for replies.
        method.

        Args:
            mocker (MockerFixture): pytest-mock fixture.
            ms_graph_mail_manager (ApiManager): Manager object.
            mock_data (SingleJson): mock json data.
        """
        # Arrange
        data = mock_data.get("get_all_mails")
        mock_get = mocker.Mock()
        mock_get.json.return_value = data
        mocker.patch.object(ms_graph_mail_manager.session, "get", return_value=mock_get)

        # Act
        email = MicrosoftGraphEmail(raw_data=mock_data.get("get_mail_details"))
        email.reply_folder_id = constants.DEFAULT_SENT_FOLDER_NAME
        replies = ms_graph_mail_manager.get_all_replies(email=email)

        # Assert
        assert isinstance(replies, list)
        assert len(replies) == 3
        assert type(replies[0]).__name__ == "MicrosoftGraphEmail"

    def test_get_attachments_valid_success(
        self,
        mocker: MockerFixture,
        ms_graph_mail_manager: ApiManager,
        mock_data: SingleJson,
    ) -> None:
        """Test to get list of MicrosoftGraphAttachment object for reply.
        method.

        Args:
            mocker (MockerFixture): pytest-mock fixture.
            ms_graph_mail_manager (ApiManager): Manager object.
            mock_data (SingleJson): mock json data.
        """
        # Arrange
        data = {"value": [mock_data.get("get_attachment")]}
        mock_get = mocker.Mock()
        mock_get.json.return_value = data
        mocker.patch.object(ms_graph_mail_manager.session, "get", return_value=mock_get)
        # Act
        email = MicrosoftGraphEmail(raw_data=mock_data.get("get_mail_details"))
        mails = ms_graph_mail_manager.get_attachments(email=email)

        # Assert
        assert isinstance(mails, list)
        assert len(mails) == 1
        assert type(mails[0]).__name__ == "MicrosoftGraphAttachment"

    def test_send_thread_reply_valid_success(
        self,
        mocker: MockerFixture,
        ms_graph_mail_manager: ApiManager,
        mock_data: SingleJson,
    ) -> None:
        """Mocking send thread reply for the API.

        Args:
            mocker (MockerFixture): pytest-mock fixture.
            ms_graph_mail_manager: Instance of ApiManager class.
            mock_data (SingleJson): mock json data.
        """
        # Arrange
        mail_content = "name"
        email = MicrosoftGraphEmail(raw_data=mock_data.get("thread_reply"))
        data = mock_data.get("thread_reply")
        mock_post = mocker.Mock()
        mock_post.status_code = 200
        mock_post.json.return_value = data
        mocker.patch.object(
            ms_graph_mail_manager.session,
            "post",
            return_value=mock_post,
        )

        # Act
        email = ms_graph_mail_manager.send_thread_reply(
            email=email,
            send_from=ms_graph_mail_manager.mail_address,
            mail_content=mail_content,
        )

        # Assert
        assert type(email).__name__ == "MicrosoftGraphEmail"
        assert email.id == data.get("id")

    def test_send_draft_email_valid_success(
        self, mocker: MockerFixture, ms_graph_mail_manager: ApiManager
    ) -> None:
        """Mocking send draft mail for the API.

        Args:
            mocker (MockerFixture): pytest-mock fixture.
            ms_graph_mail_manager: Instance of ApiManager class.
        """
        mock_post = mocker.Mock()
        mock_post.status_code = 200
        mocker.patch.object(
            ms_graph_mail_manager.session,
            "post",
            return_value=mock_post,
        )

        send_from = "abc@xyx.com"
        email_id = "abcde"

        ms_graph_mail_manager.send_draft_email(
            send_from=send_from,
            email_id=email_id,
        )

    def test_forward_email_valid_success(
        self,
        mocker: MockerFixture,
        ms_graph_mail_manager: ApiManager,
        mock_data: SingleJson,
    ) -> None:
        """Mocking forward email for the API.

        Args:
            mocker (MockerFixture): pytest-mock fixture.
            ms_graph_mail_manager: Instance of ApiManager class.
            mock_data (SingleJson): mock json data.
        """
        # Arrange
        subject = "Test Case Mail"
        mail_content = "name"
        send_from = "abc@xyx.com"
        send_to = "abc@xyx.com"
        data = mock_data.get("create_forward_draft")
        mock_post = mocker.Mock()
        mock_post.status_code = 202
        mock_post.json.return_value = data
        mocker.patch.object(
            ms_graph_mail_manager.session,
            "post",
            return_value=mock_post,
        )

        result = ms_graph_mail_manager.forward_email(
            email_id=data.get("id"),
            subject=subject,
            send_from=send_from,
            mail_content=mail_content,
            send_to=send_to,
        )

        # Assert
        assert type(result).__name__ == "MicrosoftGraphEmail"

    def test_forward_email_invalid_raise_exception(
        self, mocker: MockerFixture, ms_graph_mail_manager: ApiManager
    ) -> None:
        """Mocking forward email for the API.

        Args:
            mocker (MockerFixture): pytest-mock fixture.
            ms_graph_mail_manager: Instance of ApiManager class.
        """
        # Arrange
        email_id = (
            "AAMkADU0MDJjNjJkLTc3MzAtNGM5My04ZjM0LTZiYzVjMD"
            "I4ZTZlNQBGAAAAAADLc0XF-C8kRJTduC5WOJE-BwDby9ZjVdTJTJRS8"
            "jxrcA_oAAAAAAEMAADby9ZjVdTJTJRS8jxrcA_oAAP-k8ZMAAA"
        )
        subject = "Test Case Mail"
        send_from = "abc@xyx.com"
        send_to = "abc@xyx.com"
        mail_content = "abc"
        mock_post = mocker.Mock()
        mock_post.status_code = 400
        mock_post.raise_for_status.side_effect = Exception("MessageId is malformed.")
        mocker.patch.object(
            ms_graph_mail_manager.session,
            "post",
            return_value=mock_post,
        )

        # Act
        with pytest.raises(Exception) as error:
            ms_graph_mail_manager.forward_email(
                email_id=email_id,
                subject=subject,
                send_from=send_from,
                send_to=send_to,
                mail_content=mail_content,
            )

        # Assert
        assert "MessageId is malformed." in str(error.value)

    def test_get_folder_raises_exception(
        self,
        mocker: MockerFixture,
        ms_graph_mail_manager: ApiManager,
        mock_data: SingleJson,
    ) -> None:
        """Test to get folder datamodels.MicrosoftGraphFolder object raising exception.

        Args:
            mocker (MockerFixture): pytest-mock fixture.
            ms_graph_mail_manager (ApiManager): Manager object.
            mock_data (SingleJson): mock json data.
        """
        folder_data = mock_data.get("Invalid Folder")
        mock_get = mocker.Mock()
        mock_get.json.return_value = folder_data

        mocker.patch.object(
            ms_graph_mail_manager.session,
            "request",
            return_value=mock_get,
        )
        mocker.patch.object(
            ms_graph_mail_manager,
            "_create_folder_from_results",
            side_effect=MicrosoftGraphMailManagerError("FolderID is invalid"),
        )

        with pytest.raises(MicrosoftGraphMailManagerError):
            ms_graph_mail_manager.get_folder_by_name(
                folder_name="Éléments envoyés",
            )

    def test_mark_email_as_junk_success(
        self,
        mocker: MockerFixture,
        ms_graph_mail_manager: ApiManager,
    ) -> None:
        """Mocking mark email as junk for the API.

        Args:
            mocker (MockerFixture): pytest-mock fixture.
            ms_graph_mail_manager: Instance of ApiManager class.
        """
        mock_post = mocker.Mock()
        mock_post.status_code = 202
        mocker.patch.object(
            ms_graph_mail_manager.session,
            "post",
            return_value=mock_post,
        )
        email = mocker.create_autospec(MicrosoftGraphEmail, instance=True)
        email.mailbox_name = "user@example.com"
        email.folder_id = "abbc"
        email.id = "abc123"

        ms_graph_mail_manager.mark_email_as_junk(email=email)

    def test_mark_email_as_junk_failure(
        self,
        mocker: MockerFixture,
        ms_graph_mail_manager: ApiManager,
    ) -> None:
        """Mocking API failure for marking email as junk.

        Args:
            mocker (MockerFixture): pytest-mock fixture.
            ms_graph_mail_manager: Instance of ApiManager class.
        """
        mock_post = mocker.Mock()
        mock_post.status_code = 404
        mock_post.raise_for_status.side_effect = MicrosoftGraphMailManagerError(
            "Not Found Error"
        )
        mocker.patch.object(
            ms_graph_mail_manager.session,
            "post",
            return_value=mock_post,
        )

        email = mocker.create_autospec(MicrosoftGraphEmail, instance=True)
        email.mailbox_name = "user@example.com"
        email.folder_id = "abbc"
        email.id = "abc123"
        with pytest.raises(MicrosoftGraphMailManagerError) as e:
            ms_graph_mail_manager.mark_email_as_junk(email=email)
        assert "Not Found Error" in str(e.value)

    def test_mark_email_as_not_junk_success(
        self,
        mocker: MockerFixture,
        ms_graph_mail_manager: ApiManager,
    ) -> None:
        """Mocking mark email as not junk for the API.

        Args:
            mocker (MockerFixture): pytest-mock fixture.
            ms_graph_mail_manager: Instance of ApiManager class.
        """
        mock_post = mocker.Mock()
        mock_post.status_code = 202
        mocker.patch.object(
            ms_graph_mail_manager.session,
            "post",
            return_value=mock_post,
        )
        email = mocker.create_autospec(MicrosoftGraphEmail, instance=True)
        email.mailbox_name = "user@example.com"
        email.folder_id = "abbc"
        email.id = "abc123"

        ms_graph_mail_manager.mark_email_as_not_junk(email=email)

    def test_mark_email_as_not_junk_failure(
        self,
        mocker: MockerFixture,
        ms_graph_mail_manager: ApiManager,
    ) -> None:
        """Mocking API failure for marking email as not junk.

        Args:
            mocker (MockerFixture): pytest-mock fixture.
            ms_graph_mail_manager: Instance of ApiManager class.
        """
        mock_post = mocker.Mock()
        mock_post.status_code = 404
        mock_post.raise_for_status.side_effect = MicrosoftGraphMailManagerError(
            "Not Found Error"
        )
        mocker.patch.object(
            ms_graph_mail_manager.session,
            "post",
            return_value=mock_post,
        )

        email = mocker.create_autospec(MicrosoftGraphEmail, instance=True)
        email.mailbox_name = "user@example.com"
        email.folder_id = "abbc"
        email.id = "abc123"
        with pytest.raises(MicrosoftGraphMailManagerError) as e:
            ms_graph_mail_manager.mark_email_as_not_junk(email=email)
        assert "Not Found Error" in str(e.value)

    def test_get_user_id_success(
        self,
        mocker: MockerFixture,
        ms_graph_mail_manager: ApiManager,
        mock_data: SingleJson,
    ) -> None:
        """Test successful retrieval of user ID.

        Args:
            mocker (MockerFixture): pytest-mock fixture.
            ms_graph_mail_manager (ApiManager): Manager object.
            mock_data (SingleJson): mock json data.
        """
        user_data = mock_data.get("get_user")
        mock_get = mocker.Mock()
        mock_get.json.return_value = user_data
        mock_get.status_code = 200
        mocker.patch.object(
            ms_graph_mail_manager.session,
            "get",
            return_value=mock_get,
        )

        user_id = ms_graph_mail_manager.get_user_id(mail_address="test@example.com")

        assert user_id == user_data["id"]

    def test_get_user_oof_settings_success(
        self,
        mocker: MockerFixture,
        ms_graph_mail_manager: ApiManager,
        mock_data: SingleJson,
    ) -> None:
        """Test successful retrieval of user's Out of Office settings.

        Args:
            mocker (MockerFixture): pytest-mock fixture.
            ms_graph_mail_manager (ApiManager): Manager object.
            mock_data (SingleJson): mock json data.
        """
        oof_data = mock_data.get("get_ooo_settings", {})
        mock_get = mocker.Mock()
        mock_get.json.return_value = oof_data
        mock_get.status_code = 200
        mocker.patch.object(
            ms_graph_mail_manager.session,
            "get",
            return_value=mock_get,
        )

        oof_settings = ms_graph_mail_manager.get_user_oof_settings(
            user_id="test_user_id"
        )

        assert type(oof_settings).__name__ == "UserOOFSettings"
        assert oof_settings.availability == oof_data.get("availability")
        assert oof_settings.activity == oof_data.get("activity")
        assert oof_settings.status_message == oof_data.get("statusMessage")
        assert oof_settings.ooo_settings == oof_data.get("outOfOfficeSettings")
        assert oof_settings.is_ooo == oof_data.get("outOfOfficeSettings").get(
            "isOutOfOffice"
        )
        assert oof_settings.ooo_message == oof_data.get("outOfOfficeSettings").get(
            "message"
        )

    def test_get_user_oof_settings_json_error(
        self,
        mocker: MockerFixture,
        ms_graph_mail_manager: ApiManager,
    ) -> None:
        """Test handling of JSON error when retrieving user's Out of Office settings.

        Args:
            mocker (MockerFixture): pytest-mock fixture.
            ms_graph_mail_manager (ApiManager): Manager object.
        """
        mock_get = mocker.Mock()
        mock_get.json.side_effect = ValueError("Invalid JSON")
        mock_get.status_code = 200
        mocker.patch.object(
            ms_graph_mail_manager.session,
            "get",
            return_value=mock_get,
        )

        with pytest.raises(ValueError) as err:
            ms_graph_mail_manager.get_user_oof_settings(user_id="test_user_id")

        assert "Invalid JSON" in str(err.value)

    def test_get_user_mailbox_with_mail_field_source(
        self,
        mocker: MockerFixture,
        ms_graph_mail_manager: ApiManager,
    ) -> None:
        """Test retrieval of user's mailbox address when mail_field_source is enabled.

        Args:
            mocker (MockerFixture): pytest-mock fixture.
            ms_graph_mail_manager (ApiManager): Manager object.
        """
        ms_graph_mail_manager.mail_field_source = True
        mock_data = {"userPrincipalName": "user@example.com"}
        mock_get = mocker.Mock()
        mock_get.json.return_value = mock_data
        mock_get.status_code = 200
        mocker.patch.object(
            ms_graph_mail_manager.session,
            "get",
            return_value=mock_get,
        )
        ms_graph_mail_manager.get_user_principal_name_from_mail = mocker.Mock(
            return_value="user@example.com"
        )

        mailbox_address = ms_graph_mail_manager.get_user_mailbox(
            mail_address="user@example.com"
        )

        assert mailbox_address == "user@example.com"
        ms_graph_mail_manager.get_user_principal_name_from_mail.assert_called_once_with(
            "user@example.com"
        )

    def test_get_user_mailbox_without_mail_field_source(
        self,
        mocker: MockerFixture,
        ms_graph_mail_manager: ApiManager,
    ) -> None:
        """Test retrieval of user's mailbox address when mail_field_source is disabled.

        Args:
            mocker (MockerFixture): pytest-mock fixture.
            ms_graph_mail_manager (ApiManager): Manager object.
        """
        ms_graph_mail_manager.mail_field_source = False
        mock_data = {"userPrincipalName": "user@example.com"}
        mock_get = mocker.Mock()
        mock_get.json.return_value = mock_data
        mock_get.status_code = 200
        mocker.patch.object(
            ms_graph_mail_manager.session,
            "get",
            return_value=mock_get,
        )

        mailbox_address = ms_graph_mail_manager.get_user_mailbox(
            mail_address="test_user_id"
        )

        assert mailbox_address == "user@example.com"
