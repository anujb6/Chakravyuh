from pydantic import BaseModel, Field, field_validator
from typing import Optional

class DataRequest(BaseModel):
    symbol: str = Field(..., description="Trading symbol", min_length=1)
    timeframe: str = Field(default="1h", description="Data timeframe")
    limit: Optional[int] = Field(default=None, description="Maximum number of bars", gt=0, le=10000)
    
    @field_validator('symbol')
    def symbol_must_be_valid(cls, v):
        return v.upper().strip()
    
    @field_validator('timeframe')
    def timeframe_must_be_valid(cls, v):
        valid_timeframes = ['1h', '2h', '4h', '1d', '1w', '1mo']
        if v.lower() not in valid_timeframes:
            raise ValueError(f'Timeframe must be one of: {valid_timeframes}')
        return v.lower()