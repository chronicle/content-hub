from core.opencti_client.client import OpenCTIClient
from TIPCommon.base.action import Action
from TIPCommon.base.action.base_enrich_action import (
    EnrichAction,
    EnrichActionError,
    Entity,
)
from TIPCommon.extraction import extract_configuration_param

try:
    from SiemplifyAction import SiemplifyAction  # type: ignore[import]
except Exception:
    from soar_sdk.SiemplifyAction import SiemplifyAction


class _OpenCTIMixin:
    """Mixin providing OpenCTI integration identity, script naming, and API client setup."""

    INTEGRATION_IDENTIFIER: str = "OpenCTI"

    def __init__(self, script_name: str) -> None:
        """Initialize the instance.

        Args:
            script_name: str value.
        """
        script_name = self.build_script_name(script_name)
        super().__init__(script_name)  # type: ignore[call-arg]

        self.output_message = f"Action '{script_name}' successfully executed"
        self.error_output_message = f"Error executing action '{script_name}'"

    @property
    def soar_action(self) -> SiemplifyAction:
        """Return the underlying SiemplifyAction SDK object."""
        return super().soar_action  # type: ignore[return-value]

    @classmethod
    def build_script_name(cls, action_name: str) -> str:
        """Build a platform-compatible script name for an action."""
        return f"{cls.INTEGRATION_IDENTIFIER} - {action_name}"

    def _init_api_clients(self) -> OpenCTIClient:
        """Initialize and return the OpenCTI API client."""
        octi_url: str = extract_configuration_param(
            self.soar_action,
            provider_name=self.INTEGRATION_IDENTIFIER,
            param_name="URL",
            input_type=str,
            is_mandatory=True,
            print_value=True,
        )  # type: ignore[assignment]
        octi_token: str = extract_configuration_param(
            self.soar_action,
            provider_name=self.INTEGRATION_IDENTIFIER,
            param_name="API Token",
            input_type=str,
            is_mandatory=True,
            print_value=False,
        )  # type: ignore[assignment]
        verify_ssl: bool = extract_configuration_param(
            self.soar_action,
            provider_name=self.INTEGRATION_IDENTIFIER,
            param_name="Verify SSL",
            input_type=bool,  # type: ignore[arg-type]
            is_mandatory=False,
            default_value=True,
            print_value=True,
        )

        return OpenCTIClient(
            base_url=octi_url,
            api_token=octi_token,
            ssl_verify=verify_ssl,
        )

    @property
    def api_client(self) -> OpenCTIClient:
        """Override api_client typing."""
        return super().api_client  # type: ignore[return-value]


class BaseAction(_OpenCTIMixin, Action):
    """Base class for OpenCTI actions."""

    def __init__(self, script_name: str) -> None:
        """Initialize the instance.

        Args:
            script_name: str value.
        """
        super().__init__(script_name)

        # Track identifiers for later use in output_message
        # Only for actions that rely on self.entity_types (bulk actions)
        self._created_identifiers: list[str] = []
        self._failed_identifiers: list[str] = []

    def _on_entity_failure(self, current_entity: Entity, error: Exception) -> None:  # type: ignore[type-var]
        """Record per-entity failures.
        Called only if self.entity_types is not empty (bulk action).

        Args:
            current_entity: Entity that failed.
            error: Raised exception wrapped by SOAR framework.
        """
        if not self.entity_types:
            return  # Not a bulk action, no need to track failures

        identifier = current_entity.original_identifier

        self._failed_identifiers.append(identifier)

        # Every exception raised in _perform_action is wrapped in `EnrichActionError`
        cause = error.__cause__ if error.__cause__ is not None else error
        self.json_results[identifier] = {"execution_status": str(cause)}

    def _finalize_action_on_success(self) -> None:
        """Build the final action status message from success and failure buckets.
        Called only if self.entity_types is not empty (bulk action).
        """
        if not self.entity_types:
            return  # Not a bulk action -> output_message is already set in _perform_action

        if not self._created_identifiers and not self._failed_identifiers:
            self.result_value = False
            self.output_message = "No entities match the supported entity types."
            return

        output_parts: list[str] = []
        if self._created_identifiers:
            output_parts.append(
                "Successfully created the following entities using "
                f"{self.name}:\n {', '.join(self._created_identifiers)}\n"
            )

        if self._failed_identifiers:
            output_parts.append(
                f"The action wasn't able to create the following entities using "
                f"{self.name}:\n {', '.join(self._failed_identifiers)}\n"
            )

        self.result_value = bool(self._created_identifiers)
        self.output_message = "\n".join(output_parts)


class EntityNotFoundError(EnrichActionError):
    """Raised when an entity is not found in OpenCTI."""


class BaseEnrichAction(_OpenCTIMixin, EnrichAction):
    """Base class for OpenCTI enrichment actions."""

    def __init__(self, script_name: str) -> None:
        """Initialize the instance.

        Args:
            script_name: str value.
        """
        super().__init__(script_name)

        # Track identifiers for later use in output_message
        self._not_found_identifiers: list[str] = []
        self._failed_identifiers: list[str] = []

    def _on_entity_failure(self, current_entity: Entity, error: Exception) -> None:  # type: ignore[type-var]
        """Record per-entity enrichment failures and classify not-found cases separately.

        Args:
            current_entity: Entity that failed enrichment.
            error: Raised exception wrapped by SOAR framework.
        """
        identifier = current_entity.original_identifier

        # Every exception raised in _perform_action is wrapped in `EnrichActionError`
        cause = error.__cause__ if error.__cause__ is not None else error
        if isinstance(cause, EntityNotFoundError):
            self._not_found_identifiers.append(identifier)
        else:
            self._failed_identifiers.append(identifier)

        self.json_results[identifier] = {"execution_status": str(cause)}

    def _finalize_action_on_success(self) -> None:
        """Build the final action status message from success, not-found, and failure buckets."""
        enriched_identifiers = [e.original_identifier for e in self.entities_to_update]

        if (
            not enriched_identifiers
            and not self._not_found_identifiers
            and not self._failed_identifiers
        ):
            self.result_value = False
            self.output_message = (
                "No entities match the supported entity types. "
                "No enrichment could be performed."
            )
            return

        output_parts: list[str] = []
        if enriched_identifiers:
            output_parts.append(
                "Successfully enriched the following entities using "
                f"{self.name}:\n {', '.join(enriched_identifiers)}\n"
            )

        if self._not_found_identifiers:
            output_parts.append(
                f"The following entities were not found in "
                f"{self.name}:\n "
                f"{', '.join(self._not_found_identifiers)}\n"
            )

        if self._failed_identifiers:
            output_parts.append(
                f"The action wasn't able to enrich the following entities using "
                f"{self.name}:\n {', '.join(self._failed_identifiers)}\n"
            )

        self.result_value = bool(enriched_identifiers)
        self.output_message = "\n".join(output_parts)
