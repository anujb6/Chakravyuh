from pydantic import BaseModel, Field
from typing import Optional

class WebSocketCommand(BaseModel):
    command: str = Field(..., description="Command type (start, pause, resume, stop)")
    symbol: Optional[str] = Field(default=None, description="Trading symbol")
    timeframe: Optional[str] = Field(default="1h", description="Data timeframe")
    speed: Optional[float] = Field(default=1.0, description="Replay speed multiplier", gt=0, le=10)
    start_date: Optional[str] = Field(default=None, description="Start date for replay")