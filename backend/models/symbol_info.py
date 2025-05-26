from pydantic import BaseModel, Field
from typing import List, Dict

class SymbolInfo(BaseModel):
    symbol: str = Field(..., description="Trading symbol")
    total_bars: int = Field(..., description="Total number of bars available")
    date_range: Dict[str, str] = Field(..., description="Start and end dates")
    last_price: float = Field(..., description="Last closing price")
    available_timeframes: List[str] = Field(..., description="Supported timeframes")