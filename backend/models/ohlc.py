from pydantic import BaseModel, Field

class OHLCVBar(BaseModel):
    time: str = Field(..., description="ISO timestamp")
    open: float = Field(..., description="Opening price")
    high: float = Field(..., description="High price")
    low: float = Field(..., description="Low price") 
    close: float = Field(..., description="Closing price")