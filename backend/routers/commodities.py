# backend/routers/data_router.py

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from typing import List, Optional
import asyncio
import json

from services.commodities import CommoditiesService
from models.market_data_response import MarketDataResponse
from models.symbol_info import SymbolInfo
from models.symbol_stats import SymbolStats
from models.data_request import DataRequest
from models.date_range_request import DateRangeRequest
from models.error import ErrorResponse
from models.replay_stream_message import ReplayStreamMessage
from models.websocket_command import WebSocketCommand

class CommoditiesRouter:
    def __init__(self):
        self.router = APIRouter(prefix="/commodities", tags=["Market Data"])
        self.data_service = CommoditiesService()
        self.active_connections: dict = {}
        
        self.router.add_api_route(
            "/symbols",
            summary="Get available trading symbols",
            description="Fetch a list of all available trading symbols with their details.", 
            endpoint=self.get_available_symbols,
            methods=["GET"],
            response_model=List[SymbolInfo]
        )
        
        self.router.add_api_route(
            "/timeframes",
            summary="Get supported timeframes",
            description="Fetch a list of all supported timeframes for market data.",
            endpoint=self.get_supported_timeframes,
            methods=["GET"],
            response_model=dict
        )
        
        self.router.add_api_route(
            "/{symbol}",
            summary="Get OHLCV data for a symbol",
            description="Fetch OHLCV data for a specific trading symbol and timeframe.",
            endpoint=self.get_symbol_data,
            methods=["GET"],
            response_model=MarketDataResponse
        )
        
        self.router.add_api_route(
            "/{symbol}/range",
            summary="Get OHLCV data for a symbol in a date range",
            description="Fetch OHLCV data for a specific trading symbol within a date range.",
            endpoint=self.get_symbol_data_range,
            methods=["GET"],
            response_model=MarketDataResponse
        )
        
        self.router.add_api_route(
            "/{symbol}/stats",
            summary="Get statistics for a symbol",
            description="Fetch statistical data for a specific trading symbol.",
            endpoint=self.get_symbol_statistics,
            methods=["GET"],
            response_model=SymbolStats
        )

    async def get_available_symbols(self):
        try:
            symbols = await self.data_service.get_all_symbols()
            if not symbols:
                raise HTTPException(status_code=404, detail="No symbols found")
            return symbols
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching symbols: {str(e)}")

    async def get_supported_timeframes(self):
        try:
            timeframes = await self.data_service.get_available_timeframes()
            return {
                "timeframes": timeframes,
                "default": "1h",
                "description": {
                    "1h": "1 Hour",
                    "2h": "2 Hours", 
                    "4h": "4 Hours",
                    "1d": "1 Day",
                    "1w": "1 Week",
                    "1mo": "1 Month"
                }
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching timeframes: {str(e)}")

    async def get_symbol_data(
        self,
        symbol: str,
        timeframe: str = Query(default="1h", description="Timeframe for the data"),
        limit: Optional[int] = Query(default=None, description="Limit number of bars", gt=0, le=10000)
    ):
        try:
            validation = await self.data_service.validate_request_params(symbol, timeframe)
            if not validation['valid']:
                raise HTTPException(status_code=400, detail=validation['errors'])
            
            data = await self.data_service.get_symbol_ohlcv(symbol, timeframe, limit)
            if not data:
                raise HTTPException(status_code=404, detail=f"No data found for symbol {symbol}")
            
            return data
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")

    async def get_symbol_data_range(
        self,
        symbol: str,
        start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
        end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
        timeframe: str = Query(default="1h", description="Timeframe for the data")
    ):
        try:
            validation = await self.data_service.validate_request_params(symbol, timeframe)
            if not validation['valid']:
                raise HTTPException(status_code=400, detail=validation['errors'])
            
            data = await self.data_service.get_symbol_data_range(symbol, start_date, end_date, timeframe)
            if not data:
                raise HTTPException(status_code=404, detail=f"No data found for {symbol} in date range")
            
            return data
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching data range: {str(e)}")

    async def get_symbol_statistics(
        self,
        symbol: str,
        timeframe: str = Query(default="1h", description="Timeframe for statistics")
    ):
        try:
            validation = await self.data_service.validate_request_params(symbol, timeframe)
            if not validation['valid']:
                raise HTTPException(status_code=400, detail=validation['errors'])
            
            stats = await self.data_service.get_symbol_stats(symbol, timeframe)
            if not stats:
                raise HTTPException(status_code=404, detail=f"No statistics available for {symbol}")
            
            return stats
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching statistics: {str(e)}")
