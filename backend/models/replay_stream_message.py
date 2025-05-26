from pydantic import BaseModel, Field
from typing import Optional

from models.ohlc import OHLCVBar

class ReplayStreamMessage(BaseModel):
    type: str = Field(..., description="Message type")
    symbol: str = Field(..., description="Trading symbol")
    timeframe: str = Field(..., description="Data timeframe")
    bar: Optional[OHLCVBar] = Field(default=None, description="OHLCV bar data")
    message: Optional[str] = Field(default=None, description="Status message")
