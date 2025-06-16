import httpx
from typing import Dict, List, Optional
from pydantic import BaseModel

class SymbolInfo(BaseModel):
    symbol: str
    total_bars: int
    date_range: Dict[str, str]
    last_price: float
    available_timeframes: List[str]

class OHLCVBar(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float

class MarketDataResponse(BaseModel):
    symbol: str 
    timeframe: str 
    data: List[OHLCVBar] 
    count: int
    date_range: Dict[str, str]   

class SymbolStats(BaseModel):
    symbol: str 
    timeframe: str 
    current_price: float 
    price_change: float 
    price_change_percent: float 
    high_24h: float 
    low_24h: float
    last_updated: str

class APIClient:
    def __init__(self, base_url: str = "http://localhost:8000/commodities"):
        self.base_url = base_url
        self.client = httpx.Client()

    def get_available_symbols(self) -> List[SymbolInfo]:
        response = self.client.get(f"{self.base_url}/symbols")
        response.raise_for_status()
        return [SymbolInfo(**item) for item in response.json()]

    def get_supported_timeframes(self) -> dict:
        response = self.client.get(f"{self.base_url}/timeframes")
        response.raise_for_status()
        return response.json()

    def get_symbol_data(self, symbol: str, timeframe: str, limit: Optional[int] = None) -> MarketDataResponse:
        params = {"timeframe": timeframe}
        if limit is not None:
            params["limit"] = limit
        response = self.client.get(f"{self.base_url}/{symbol}", params=params)
        response.raise_for_status()
        return MarketDataResponse(**response.json())

    def get_symbol_data_range(
        self,
        symbol: str,
        timeframe: str,
        start: str,
        end: str
    ) -> MarketDataResponse:
        params = {"timeframe": timeframe, "start": start, "end": end}
        response = self.client.get(f"{self.base_url}/{symbol}/range", params=params)
        response.raise_for_status()
        return MarketDataResponse(**response.json())

    def get_symbol_statistics(self, symbol: str) -> SymbolStats:
        response = self.client.get(f"{self.base_url}/{symbol}/stats")
        response.raise_for_status()
        return SymbolStats(**response.json())

    def close(self):
        self.client.close()
