"""Variable Set models for org/project-scoped shared variables."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class VariableSetVariable(BaseModel):
    """A variable belonging to a variable set."""

    id: str
    key: str
    value: str | None = None
    description: str | None = None
    category: str  # "terraform" or "env"
    hcl: bool = False
    sensitive: bool = False

    model_config = ConfigDict(populate_by_name=True)

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "VariableSetVariable":
        attrs = data.get("attributes", {})
        return cls.model_construct(
            id=data["id"],
            key=attrs.get("key", ""),
            value=attrs.get("value"),
            description=attrs.get("description"),
            category=attrs.get("category", "terraform"),
            hcl=attrs.get("hcl", False),
            sensitive=attrs.get("sensitive", False),
        )

    @property
    def display_value(self) -> str:
        if self.sensitive:
            return "••••••••"
        return self.value or ""

    @property
    def is_terraform_var(self) -> bool:
        return self.category == "terraform"

    @property
    def is_env_var(self) -> bool:
        return self.category == "env"

    def __repr__(self) -> str:
        """String representation masking sensitive values."""
        return f"VariableSetVariable(key={self.key!r}, value={self.display_value!r}, sensitive={self.sensitive!r})"


class VariableSet(BaseModel):
    """Terraform Cloud variable set (org or project scoped)."""

    id: str
    name: str
    description: str | None = None
    global_: bool = Field(False, alias="global")
    var_count: int = 0
    workspace_count: int = 0

    model_config = ConfigDict(populate_by_name=True)

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "VariableSet":
        attrs = data.get("attributes", {})
        return cls(
            id=data["id"],
            **{
                "global": attrs.get("global", False),
            },
            name=attrs.get("name", ""),
            description=attrs.get("description"),
            var_count=attrs.get("var-count", 0),
            workspace_count=attrs.get("workspace-count", 0),
        )
