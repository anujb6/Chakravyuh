
from typing import List
from altair import Dict
from pydantic import BaseModel

from app.models.ohlcv_bar import OHLCVBar

class MarketDataResponse(BaseModel):
    symbol: str 
    timeframe: str 
    data: List[OHLCVBar] 
    count: int
    date_range: Dict[str, str]   