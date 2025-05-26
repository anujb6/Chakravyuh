from pydantic import BaseModel, Field

class SymbolStats(BaseModel):
    symbol: str = Field(..., description="Trading symbol")
    timeframe: str = Field(..., description="Data timeframe")
    current_price: float = Field(..., description="Current price")
    price_change: float = Field(..., description="Price change from previous bar")
    price_change_percent: float = Field(..., description="Percentage price change")
    high_24h: float = Field(..., description="24h high")
    low_24h: float = Field(..., description="24h low")
    last_updated: str = Field(..., description="Last update timestamp")