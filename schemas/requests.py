from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = Field(default=None, max_length=100)

class InventoryItemRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    category: str = Field(
        ...,
        pattern="^(PANTRY_DRY|DAIRY|PRODUCE|MEAT|FROZEN|BAKERY|SPICES|BEVERAGES|HOUSEHOLD)$"
    )
    quantity: float = Field(..., gt=0, le=10000)
    unit: str = Field(..., pattern="^(pcs|g|ml|kg|l)$")
    cost_per_unit: float = Field(..., ge=0, le=50000)
    store: Optional[str] = Field(default=None, max_length=100)
    expiry_date: Optional[datetime] = None

    @field_validator("expiry_date")
    @classmethod
    def expiry_must_not_be_past(cls, v):
        if v and v < datetime.utcnow():
            raise ValueError("Expiry date must be in the future")
        return v
