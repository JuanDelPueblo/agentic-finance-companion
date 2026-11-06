from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

# Exact money amounts with two decimal places. Serialized as JSON strings (e.g. "12.50")
# so no precision is lost in transit; parse them with a decimal library on the client.
Money = Annotated[Decimal, Field(max_digits=14, decimal_places=2)]

# ISO 4217 currency code.
CurrencyCode = Annotated[str, Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")]


class Schema(BaseModel):
    """Base for API schemas: reject unknown fields, so contract drift fails loudly."""

    model_config = ConfigDict(extra="forbid")


class ErrorResponse(Schema):
    detail: str
    code: str | None = None
    requires_relink: bool = False
