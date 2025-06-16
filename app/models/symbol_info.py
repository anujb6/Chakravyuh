from typing import List
from altair import Dict
from pydantic import BaseModel


class SymbolInfo(BaseModel):
    symbol: str
    total_bars: int
    date_range: Dict[str, str]
    last_price: float
    available_timeframes: List[str]
    
