from typing import List, Optional, Dict, Any
import pandas as pd
from datetime import datetime, timedelta
from repository.commodities import CommoditiesRepository

class CommoditiesService:
    def __init__(self):
        self.data_repo = CommoditiesRepository()
        self.cache = {}
    
    async def get_all_symbols(self) -> List[Dict[str, Any]]:
        try:
            symbols = self.data_repo.get_available_symbols()
            symbol_data = []
            
            for symbol in symbols:
                info = self.data_repo.get_data_info(symbol)
                if info:
                    symbol_data.append(info)
            
            return symbol_data
            
        except Exception as e:
            print(f"Error in get_all_symbols service: {e}")
            return []
    
    async def get_symbol_ohlcv(self, symbol: str, timeframe: str = '1h', limit: Optional[int] = None) -> Optional[Dict[str, Any]]:
        try:
            if not self.data_repo.validate_symbol_exists(symbol):
                return None
            
            if limit:
                df = self.data_repo.get_latest_data(symbol, limit, timeframe)
            else:
                df = self.data_repo.get_symbol_data(symbol, timeframe)
            
            if df is None:
                return None
            
            return self._format_ohlcv_response(df, symbol, timeframe)
            
        except Exception as e:
            print(f"Error in get_symbol_ohlcv service: {e}")
            return None
    
    async def get_symbol_data_range(self, symbol: str, start_date: str, end_date: str, timeframe: str = '1h') -> Optional[Dict[str, Any]]:
        try:
            df = self.data_repo.get_symbol_data_range(symbol, start_date, end_date, timeframe)
            if df is None:
                return None
            
            return self._format_ohlcv_response(df, symbol, timeframe)
            
        except Exception as e:
            print(f"Error in get_symbol_data_range service: {e}")
            return None
    
    async def get_replay_data_stream(self, symbol: str, timeframe: str = '1h', start_date: Optional[str] = None):
        try:
            if start_date:
                df = self.data_repo.get_symbol_data_range(
                    symbol, 
                    start_date, 
                    (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d'),
                    timeframe
                )
            else:
                df = self.data_repo.get_symbol_data(symbol, timeframe)
            
            if df is None:
                return
            
            for timestamp, row in df.iterrows():
                bar_data = {
                    'timestamp': timestamp.isoformat(),
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close'])
                }
                yield bar_data
                
        except Exception as e:
            print(f"Error in replay stream for {symbol}: {e}")
            return
    
    async def validate_request_params(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        errors = []
        
        if not self.data_repo.validate_symbol_exists(symbol):
            errors.append(f"Symbol '{symbol}' not found")
        
        if timeframe not in self.data_repo.timeframe_multipliers:
            errors.append(f"Timeframe '{timeframe}' not supported. Available: {list(self.data_repo.timeframe_multipliers.keys())}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    async def get_available_timeframes(self) -> List[str]:
        return list(self.data_repo.timeframe_multipliers.keys())
    
    async def get_symbol_stats(self, symbol: str, timeframe: str = '1h') -> Optional[Dict[str, Any]]:
        try:
            df = self.data_repo.get_symbol_data(symbol, timeframe)
            if df is None:
                return None
            
            latest_bar = df.iloc[-1]
            previous_bar = df.iloc[-2] if len(df) > 1 else df.iloc[-1]
            
            price_change = latest_bar['close'] - previous_bar['close']
            price_change_pct = (price_change / previous_bar['close']) * 100
            
            return {
                'symbol': symbol.upper(),
                'timeframe': timeframe,
                'current_price': float(latest_bar['close']),
                'price_change': float(price_change),
                'price_change_percent': float(price_change_pct),
                'high_24h': float(df['high'].tail(24).max()) if timeframe == '1h' else float(df['high'].iloc[-1]),
                'low_24h': float(df['low'].tail(24).min()) if timeframe == '1h' else float(df['low'].iloc[-1]),
                'last_updated': df.index[-1].isoformat()
            }
            
        except Exception as e:
            print(f"Error getting stats for {symbol}: {e}")
            return None
    
    def _format_ohlcv_response(self, df: pd.DataFrame, symbol: str, timeframe: str) -> Dict[str, Any]:
        try:
            bars = []
            for timestamp, row in df.iterrows():
                bars.append({
                    'time': timestamp.isoformat(),
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close'])
                })
            
            return {
                'symbol': symbol.upper(),
                'timeframe': timeframe,
                'data': bars,
                'count': len(bars),
                'date_range': {
                    'start': df.index.min().isoformat(),
                    'end': df.index.max().isoformat()
                }
            }
            
        except Exception as e:
            print(f"Error formatting response: {e}")
            return {
                'symbol': symbol.upper(),
                'timeframe': timeframe,
                'data': [],
                'count': 0,
                'error': str(e)
            }