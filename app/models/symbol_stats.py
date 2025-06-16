from pydantic import BaseModel


class SymbolStats(BaseModel):
    symbol: str 
    timeframe: str 
    current_price: float 
    price_change: float 
    price_change_percent: float 
    high_24h: float 
    low_24h: float
    last_updated: str