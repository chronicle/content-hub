"""A mocked app.houdin.io: launch answers a scanID, result leaves a scan out until it is 'done'."""

from __future__ import annotations

import copy
import json
from typing import TYPE_CHECKING

from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession

from .common import INTEGRATION_PATH

if TYPE_CHECKING:
    from collections.abc import Callable

    from TIPCommon.types import SingleJson

EXAMPLE_PATH = INTEGRATION_PATH / "resources" / "scan_artifact_JsonResult_example.json"
EXAMPLE_DOCUMENT: SingleJson = json.loads(EXAMPLE_PATH.read_text())


def document_for(artifact: str, scan_id: str, score: int | None = 8) -> SingleJson:
    """The example scan document, re-addressed to another artifact and score."""
    document: SingleJson = copy.deepcopy(EXAMPLE_DOCUMENT)
    document["scanID"] = scan_id
    document["artifact"] = artifact
    mesmer: SingleJson = document["scanResults"]["mesmer"]["result"]
    if score is None:
        del document["scanResults"]["mesmer"]
    else:
        mesmer["globalScore"] = score
    return document


class HoudinSession(MockSession[MockRequest, MockResponse, None]):
    def __init__(self) -> None:
        super().__init__()
        self.key_valid: bool = True
        self.launched: dict[str, str] = {}  # scanID -> artifact
        self.running: set[str] = set()  # scanIDs still "In progress"
        self.scores: dict[str, int | None] = {}  # artifact -> score
        self.refuse: dict[str, tuple[int, str]] = {}  # artifact -> (status, body)
        self.launch_status: str = "In progress"
        self.server_errors_left: int = 0

    def get_routed_functions(self) -> list[Callable[[MockRequest], MockResponse]]:
        return [self.ping, self.launch, self.result]

    def _rejected(self) -> MockResponse | None:
        # A requests.Response is falsy below 400, so callers must test `is not None`.
        if self.server_errors_left > 0:
            self.server_errors_left -= 1
            return MockResponse(content="Internal error", status_code=500)
        if not self.key_valid:
            return MockResponse(content={"error": "Invalid API Key"}, status_code=400)
        return None

    @router.post(r"/api/v1/ping")
    def ping(self, request: MockRequest) -> MockResponse:
        if (rejected := self._rejected()) is not None:
            return rejected
        return MockResponse(content={"message": "API Key is valid"})

    @router.post(r"/api/v1/scan/launch")
    def launch(self, request: MockRequest) -> MockResponse:
        if (rejected := self._rejected()) is not None:
            return rejected
        artifact: str = request.kwargs["json"]["artifact"]
        if artifact in self.refuse:
            status, body = self.refuse[artifact]
            return MockResponse(content=body, status_code=status)
        scan_id: str = f"houdin-{len(self.launched) + 1:08d}-0000-4000-8000-000000000000"
        self.launched[scan_id] = artifact
        if self.launch_status != "Done":
            self.running.add(scan_id)
        return MockResponse(content={"scanID": scan_id, "status": self.launch_status})

    def _document(self, scan_id: str) -> SingleJson | None:
        if scan_id not in self.launched or scan_id in self.running:
            return None
        artifact: str = self.launched[scan_id]
        return document_for(artifact, scan_id, self.scores.get(artifact, 8))

    @router.post(r"/api/v1/scan/result")
    def result(self, request: MockRequest) -> MockResponse:
        if (rejected := self._rejected()) is not None:
            return rejected
        scan_ids: list[str] = request.kwargs["json"]["scanIDs"]
        results: dict[str, SingleJson] = {}
        for scan_id in scan_ids:
            document: SingleJson | None = self._document(scan_id)
            if document is not None:
                results[scan_id] = document
        return MockResponse(content={"results": results, "retrieved": len(results), "requested": len(scan_ids)})

    def finish(self, *artifacts: str) -> None:
        """Mark the scans of these artifacts (all of them when none given) as done."""
        for scan_id, artifact in self.launched.items():
            if not artifacts or artifact in artifacts:
                self.running.discard(scan_id)

    def result_reads(self) -> list[list[str]]:
        """The scanIDs asked for by each POST /scan/result, in order."""
        return [
            record.request.kwargs["json"]["scanIDs"]
            for record in self.request_history
            if record.request.url.path == "/api/v1/scan/result"
        ]
