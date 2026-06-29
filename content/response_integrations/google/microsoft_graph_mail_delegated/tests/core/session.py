from __future__ import annotations

from TIPCommon.types import SingleJson
from core.datamodels import (
    MicrosoftGraphEmail,
    MicrosoftGraphFolder,
    MicrosoftGraphAttachment,
    UserOOFSettings,
)
from tests.core.product import (
    MicrosoftGraphMailDelegated,
)
from tests.common import (
    FOLDER_FAILED_JSON,
    MAIL_FAILED_JSON,
    MAILS_FAILED_JSON,
    OAUTH_TOKEN_JSON,
    SEARCH_QUERY_DATA,
    USER_FAILED_JSON,
)
from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction


class MsGraphSession(
    MockSession[MockRequest, MockResponse, MicrosoftGraphMailDelegated]
):
    def get_routed_functions(self) -> list[RouteFunction]:
        return [
            self.mark_email_as_junk,
            self.mark_email_as_not_junk,
            self.get_user,
            self.get_folders,
            self.get_email,
            self.create_draft_email,
            self.send_draft_email,
            self.get_mailbox_account_out_of_facility_settings,
            self.get_emails,
            self.move_email_to_folder,
            self.get_email_content,
            self.send_thread_reply,
            self.save_evidence,
            self.forward_email,
            self.update_entities,
            self.delete_email,
            self.get_attachments_from_email,
            self.get_attachment_content,
            self.search_query,
            self.list_users,
            self.handle_batch,
            get_oauth_token,
        ]

    @router.get("/v1.0/[a-zA-Z0-9]+/users")
    def list_users(self, request: MockRequest) -> MockResponse:
        """Handle list users request."""
        return MockResponse(content={"value": [self._product.get_user()]}, status_code=200)

    @router.get("/v1.0/[a-zA-Z0-9]+/users/[a-zA-Z0-9@.]+")
    def get_user(self, request: MockRequest) -> MockResponse:
        """Handle mailbox user request."""
        mailbox: str = request.url.path.split("/")[-1]
        if "invalid" in mailbox:
            return MockResponse(
                content=USER_FAILED_JSON,
                status_code=404,
            )

        return MockResponse(content=self._product.get_user(), status_code=200)

    @router.get("/v1.0/[a-zA-Z0-9-]+/users/[a-zA-Z0-9@.]+/mailFolders")
    def get_folders(self, request) -> MockResponse:
        """Handle get folders request."""
        folder_name: str = request.kwargs.get("params", {}).get("$filter")
        if folder_name:
            if "invalidFolder" in folder_name:
                return MockResponse(content=FOLDER_FAILED_JSON, status_code=200)

        folder: MicrosoftGraphFolder = self._product.get_folders()[0]
        content: SingleJson = {"value": [folder.to_json()]}

        return MockResponse(content=content, status_code=200)

    @router.get(
        "/v1.0/[a-zA-Z0-9]+/users/[a-zA-Z0-9@.]+/mailFolders/[a-zA-Z0-9-_=]+/"
        "messages/[a-zA-Z0-9-_=]+"
    )
    def get_email(self, request: MockRequest) -> MockResponse:
        """Handle get email request."""
        mail_id: str = request.url.path.split("/")[-1]
        if "InvalidMailId" in request.url.path:
            return MockResponse(
                content=MAIL_FAILED_JSON,
                status_code=404,
            )
        mail: MicrosoftGraphEmail = self._product.get_email(mail_id)

        return MockResponse(mail.to_json(), status_code=200)

    @router.post(
        "/beta/[a-zA-Z0-9]+/users/[a-zA-Z0-9@.]+/mailFolders/[a-zA-Z0-9-_=]+/"
        "messages/[a-zA-Z0-9-_=]+/microsoft.graph.markAsJunk"
    )
    def mark_email_as_junk(self, request) -> MockResponse:
        """Handle mark email as junk request."""
        email_id: str = request.url.path.split("/")[-2]
        updated_email: MicrosoftGraphEmail = self._product.mark_email_as_junk(email_id)

        return MockResponse(updated_email.to_json(), status_code=200)

    @router.post(
        "/beta/[a-zA-Z0-9]+/users/[a-zA-Z0-9@.]+/mailFolders/[a-zA-Z0-9-_=]+/"
        "messages/[a-zA-Z0-9-_=]+/microsoft.graph.markAsNotJunk"
    )
    def mark_email_as_not_junk(self, request: MockRequest) -> MockResponse:
        """Handle mark email as not junk request"""
        email_id: str = request.url.path.split("/")[-2]
        email: MicrosoftGraphEmail = self._product.mark_email_as_not_junk(email_id)
        return MockResponse(email.to_json(), status_code=200)

    @router.post("/v1.0/[a-zA-Z0-9]+/users/[a-zA-Z0-9@.]+/messages")
    def create_draft_email(self, request: MockRequest) -> MockResponse:
        """Handle create draft email request."""
        email: MicrosoftGraphEmail = self._product.get_emails()[0]
        email_data: SingleJson = email.to_json()
        email_data.update(request.kwargs.get("json", {}))
        return MockResponse(
            content=email_data,
            status_code=201,
        )

    @router.post(
        "/v1.0/[a-zA-Z0-9]+/users/[a-zA-Z0-9@.]+/messages/[a-zA-Z0-9-_=]+/send"
    )
    def send_draft_email(self, _: MockRequest) -> MockResponse:
        return MockResponse(content="", status_code=202)

    @router.post(
        "/v1.0/[a-zA-Z0-9]+/users/[a-zA-Z0-9@.]+/messages/[a-zA-Z0-9-_=]+/createReply"
    )
    def send_thread_reply(self, request: MockRequest) -> MockResponse:
        """Handle send thread reply request."""
        email_id: str = request.url.path.split("/")[-2]
        email: MicrosoftGraphEmail = self._product.get_email(email_id)
        return MockResponse(content=email.to_json(), status_code=200)

    @router.get(
        "/v1.0/[a-zA-Z0-9-]+/users/[a-zA-Z0-9@.]+/mailFolders/[a-zA-Z0-9-_=]+/messages"
    )
    def get_emails(self, request: MockRequest) -> MockResponse:
        """Handle get emails request."""
        if "VoteMailInProgressId" in request.url.path:
            return MockResponse(content=MAILS_FAILED_JSON)

        emails = self._product.get_emails()
        if emails[0].id == "NoReplyID":
            emails[0].raw_data["sender"]["emailAddress"][
                "address"
            ] = "noreply@example.com"
            return MockResponse(
                content={"value": [emails[0].to_json()]},
                status_code=200,
            )

        return MockResponse(
            content={"value": [email.to_json() for email in emails]},
            status_code=200,
        )

    @router.get("/beta/communications/presences/[a-zA-Z0-9-]+")
    def get_mailbox_account_out_of_facility_settings(
        self,
        _: MockRequest,
    ) -> MockResponse:
        """Handle get mailbox account out of facility settings request."""
        user_oof_settings: UserOOFSettings = self._product.get_user_oof_settings()
        return MockResponse(content=user_oof_settings.to_json(), status_code=200)

    @router.post(
        "/v1.0/[a-zA-Z0-9]+/users/[a-zA-Z0-9@.]+/mailFolders/[a-zA-Z0-9-_=]+/"
        "messages/[a-zA-Z0-9-_=]+/move"
    )
    def move_email_to_folder(self, request: MockRequest) -> MockResponse:
        """Handle move email to folder request."""
        email_id: str = request.url.path.split("/")[-2]
        email: MicrosoftGraphEmail = self._product.get_email(email_id)
        return MockResponse(
            content=email.to_json(),
            status_code=201,
        )

    @router.post(
        "/v1.0/[a-zA-Z0-9]+/users/[a-zA-Z0-9@.]+/messages/[a-zA-Z0-9-_=]+/createForward"
    )
    def forward_email(self, request: MockRequest) -> MockResponse:
        """Handle forward email request."""
        email_id: str = request.url.path.split("/")[-2]
        forwarded_email: MicrosoftGraphEmail = self._product.get_email(email_id)

        return MockResponse(content=forwarded_email.to_json(), status_code=201)

    @router.get(
        r"/v1.0/[a-zA-Z0-9]+/users/[a-zA-Z0-9@.]+/messages/[a-zA-Z0-9-_=]+/\$value$"
    )
    def get_email_content(self, _: MockRequest) -> MockResponse:
        return MockResponse(content="mock content", status_code=200)

    @router.delete(
        "/v1.0/[a-zA-Z0-9]+/users/[a-zA-Z0-9@.]+/mailFolders/[a-zA-Z0-9-_=]+/"
        "messages/[a-zA-Z0-9-_=]+"
    )
    def delete_email(self, request: MockRequest) -> MockResponse:
        """Handle delete email request."""
        email_id: str = request.url.path.split("/")[-1]
        self._product.delete_email(email_id)
        return MockResponse(
            content="",
            status_code=201,
        )

    @router.get(
        "/v1.0/[a-zA-Z0-9]+/users/[a-zA-Z0-9@.]+/mailFolders/[a-zA-Z0-9-_=]+/"
        "messages/[a-zA-Z0-9-_=]+/attachments"
    )
    def get_attachments_from_email(self, request: MockRequest) -> MockResponse:
        """Handle get attachments from email request."""
        attachment: MicrosoftGraphAttachment = self._product.get_attachments()[0]
        email_data: SingleJson = {"value": [attachment.to_json()]}
        email_data.update(request.kwargs.get("json", {}))
        return MockResponse(
            content=email_data,
            status_code=200,
        )

    @router.get(
        "/v1.0/[a-zA-Z0-9]+/users/[a-zA-Z0-9@.]+/mailFolders/[a-zA-Z0-9-_=]+/"
        r"messages/[a-zA-Z0-9-_=]+/attachments/[a-zA-Z0-9-_=]+/\$value$"
    )
    def get_attachment_content(self, _) -> MockResponse:
        """Handle get attachment content request."""
        return MockResponse(content="some_text", status_code=200)

    @router.post("/api/external/v1/sdk/UpdateEntities")
    def update_entities(self, _: MockRequest) -> MockResponse:
        return MockResponse(status_code=201)

    @router.post("/api/external/v1/cases/AddEvidence/")
    def save_evidence(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content={
                "value": [
                    {
                        "sender": "sender@example.com",
                        "recipient": "recipient@example.com",
                        "subject": "Test Email",
                        "body": "This is a test email body.",
                        "attachments": [
                            {"filename": "attachment1.pdf", "content": "pdf_content"},
                            {"filename": "attachment2.txt", "content": "text_content"},
                        ],
                    }
                ]
            },
            status_code=200,
        )

    @router.post("/v1.0/search/query")
    def search_query(self, _: MockRequest) -> MockResponse:
        return MockResponse(content=SEARCH_QUERY_DATA, status_code=200)
    @router.post("/v1.0/\\$batch")
    def handle_batch(self, request: MockRequest) -> MockResponse:
        import json
        try:
            req_data = json.loads(request.kwargs.get("data", "{}"))
            responses = []
            for req in req_data.get("requests", []):
                responses.append({
                    "id": req.get("id"),
                    "status": 200,
                    "body": {"value": []}
                })
            return MockResponse(content={"responses": responses}, status_code=200)
        except Exception:
            return MockResponse(content={"responses": []}, status_code=200)


@router.post("/[a-zA-Z0-9-]+/oauth2/v2.0/token")
def get_oauth_token(request: MockRequest) -> MockResponse:
    """Get an OAuth token"""
    if "raise_error" in request.kwargs["data"].values():
        return MockResponse(
            content={
                "error": {
                    "message": "Failed to authenticate to MicrosoftGraphMailDelegated",
                    "errors": [{"errorMessage": "Wrong Credentials!"}],
                }
            },
            status_code=400,
        )

    return MockResponse(OAUTH_TOKEN_JSON)
