from __future__ import annotations

import os
from typing import TYPE_CHECKING

import requests

from TIPCommon.extraction import extract_action_param
from TIPCommon.validation import ParameterValidator
from google_threat_intelligence.core import api_data_parser as parser
from google_threat_intelligence.core.base_action import BaseAction
from google_threat_intelligence.core.constants import (
    AGENT_CONNECTIVITY_ERROR_MESSAGE,
    AGENT_DIRECTORY_PATHS_ERROR_MESSAGE,
    AGENT_EMPTY_FILES_ERROR_MESSAGE,
    AGENT_MISSING_SESSION_ID_ERROR_MESSAGE,
    AGENT_NO_FINAL_RESPONSE_ERROR_MESSAGE,
    AGENT_NO_RESPONSE_TEXT_MESSAGE,
    ASK_THREAT_INTELLIGENCE_AGENT_SCRIPT_NAME,
    INTEGRATION_DISPLAY_NAME,
)
from google_threat_intelligence.core.exceptions import GoogleThreatIntelligenceExceptions
from google_threat_intelligence.core.utils import clean_file_path, verify_paths_accessibility

if TYPE_CHECKING:
    from TIPCommon.types import Entity

    from google_threat_intelligence.core.data_models import AgenticSession


class AskThreatIntelligenceAgent(BaseAction):
    """Action to execute prompts with the Google Threat Intelligence Agent."""

    def _extract_action_parameters(self) -> None:
        """Extract action input parameters."""
        self.params.prompt = extract_action_param(
            self.soar_action,
            param_name="Prompt",
            is_mandatory=True,
            print_value=True,
        )
        self.params.session_id = extract_action_param(
            self.soar_action,
            param_name="Session ID",
            is_mandatory=False,
            print_value=True,
        )
        self.params.file_paths = extract_action_param(
            self.soar_action,
            param_name="File Paths",
            is_mandatory=False,
            remove_whitespaces=False,
            print_value=True,
        )
        self.params.delete_session = extract_action_param(
            self.soar_action,
            param_name="Delete Session After Completion",
            input_type=bool,
            default_value=False,
            print_value=True,
        )

    def _validate_params(self) -> None:
        """Validate action input parameters."""
        validator = ParameterValidator(self.soar_action)
        self.params.file_paths = validator.validate_csv(
            param_name="File Paths",
            csv_string=self.params.file_paths,
            print_value=True,
        )
        if self.params.file_paths:
            self.params.file_paths = list(
                dict.fromkeys(filter(None, map(clean_file_path, self.params.file_paths)))
            )

    def _perform_action(self, _: Entity | None = None) -> None:
        """Submit the prompt and return the agent's answer from the synchronous response."""
        self._verify_connectivity()
        file_paths = self.params.file_paths or []
        if file_paths:
            self._verify_file_paths(file_paths)

        self.logger.info("Submitting prompt to GTI Agent and waiting for agent response...")
        session = parser.build_agentic_turn_object(
            self.api_client.post_agent_prompt(
                prompt=self.params.prompt,
                session_id=self.params.session_id or None,
                file_paths=file_paths or None,
            )
        )
        session_id = self.params.session_id or session.session_id
        if not session_id:
            raise GoogleThreatIntelligenceExceptions(AGENT_MISSING_SESSION_ID_ERROR_MESSAGE)

        try:
            self._complete_action(session, session_id)
        finally:
            if self.params.delete_session:
                self._delete_session_safely(session_id)

    def _verify_connectivity(self) -> None:
        """Verify connectivity to Google Threat Intelligence before submitting the prompt."""
        self.logger.info("Connecting to Google Threat Intelligence API...")
        try:
            self.api_client.test_connectivity()
        except (GoogleThreatIntelligenceExceptions, requests.exceptions.RequestException) as error:
            self.logger.exception(error)
            raise GoogleThreatIntelligenceExceptions(AGENT_CONNECTIVITY_ERROR_MESSAGE) from error

    def _verify_file_paths(self, file_paths: list[str]) -> None:
        """Verify that every file path points to an existing, readable and non-empty file."""
        directories = [file_path for file_path in file_paths if os.path.isdir(file_path)]
        if directories:
            raise GoogleThreatIntelligenceExceptions(
                AGENT_DIRECTORY_PATHS_ERROR_MESSAGE.format(paths=", ".join(directories))
            )

        verify_paths_accessibility(file_paths=file_paths, logger=self.logger)
        empty_files = [file_path for file_path in file_paths if not os.path.getsize(file_path)]
        if empty_files:
            raise GoogleThreatIntelligenceExceptions(
                AGENT_EMPTY_FILES_ERROR_MESSAGE.format(paths=", ".join(empty_files))
            )

    def _complete_action(self, session: AgenticSession, session_id: str) -> None:
        """Set the action result from the agent's final response to the submitted prompt.

        Raises:
            GoogleThreatIntelligenceExceptions: If the response has no final answer of the agent.
        """
        if not session.is_completed:
            raise GoogleThreatIntelligenceExceptions(
                AGENT_NO_FINAL_RESPONSE_ERROR_MESSAGE.format(session_id=session_id)
            )

        self.json_results = session.to_json()
        if session.response_text:
            self.result_value = True
            self.output_message = f"Successfully executed prompt in {INTEGRATION_DISPLAY_NAME}."
        else:
            self.result_value = False
            self.output_message = AGENT_NO_RESPONSE_TEXT_MESSAGE.format(session_id=session_id)

    def _delete_session_safely(self, session_id: str) -> None:
        """Delete the session and log any error without failing the action."""
        try:
            self.logger.info(f"Deleting session {session_id} as requested...")
            self.api_client.delete_agent_session(session_id)
        except (GoogleThreatIntelligenceExceptions, requests.exceptions.RequestException) as error:
            self.logger.error(f"Failed to delete session {session_id}. Error: {error}")


def main() -> None:
    """Execute action script entrypoint."""
    AskThreatIntelligenceAgent(ASK_THREAT_INTELLIGENCE_AGENT_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
