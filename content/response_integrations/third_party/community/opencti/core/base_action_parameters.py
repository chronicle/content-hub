from pydantic import BaseModel, ConfigDict, model_validator


class BaseActionParameters(BaseModel):
    """Base class for action parameters."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_default=True,
    )

    @model_validator(mode="before")
    @classmethod
    def _remove_empty_strings(cls, values: dict) -> dict:
        """Remove empty string fields."""
        sanitized_values = {}

        for key, value in values.items():
            if value is None:
                continue
            if isinstance(value, str) and value.strip() == "":
                continue
            sanitized_values[key] = value

        return sanitized_values
