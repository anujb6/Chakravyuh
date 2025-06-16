from pydantic import BaseModel


class OHLCVBar(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float
