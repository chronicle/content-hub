from __future__ import annotations
from vertex_ai.core.VertexAIBaseAction import BaseAction
from vertex_ai.core.VertexAIConstants import PING_SCRIPT_NAME

SUCCESS_MESSAGE = (
    "Successfully connected to Vertex AI with the provided connection parameters!"
)
ERROR_MESSAGE = "Failed to connect to Vertex AI!"


class Ping(BaseAction):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = SUCCESS_MESSAGE
        self.error_output_message = ERROR_MESSAGE

    def _perform_action(self, _=None) -> None:
        publisher_name = self.params.default_publisher_name
        self.api_client.test_connectivity(
            model_id=self.params.default_model, publisher_name=publisher_name,
        )


def main() -> None:
    Ping(PING_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
