from pydantic import BaseModel, Field
from typing import List, Optional

class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    details: Optional[List[str]] = Field(default=None, description="Additional error details")