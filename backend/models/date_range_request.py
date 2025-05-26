
from pydantic import BaseModel, Field, field_validator
from datetime import datetime

class DateRangeRequest(BaseModel):
    symbol: str = Field(..., description="Trading symbol", min_length=1)
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    timeframe: str = Field(default="1h", description="Data timeframe")
    
    @field_validator('symbol')
    def symbol_must_be_valid(cls, v):
        return v.upper().strip()
    
    @field_validator('timeframe')
    def timeframe_must_be_valid(cls, v):
        valid_timeframes = ['1h', '2h', '4h', '1d', '1w', '1mo']
        if v.lower() not in valid_timeframes:
            raise ValueError(f'Timeframe must be one of: {valid_timeframes}')
        return v.lower()
    
    @field_validator('start_date', 'end_date')
    def date_must_be_valid(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')