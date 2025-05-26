from pydantic import BaseModel, Field
from typing import List, Dict
from models.ohlc import OHLCVBar

class MarketDataResponse(BaseModel):
    symbol: str = Field(..., description="Trading symbol")
    timeframe: str = Field(..., description="Data timeframe")
    data: List[OHLCVBar] = Field(..., description="OHLCV bars")
    count: int = Field(..., description="Number of bars returned")
    date_range: Dict[str, str] = Field(..., description="Date range of data")