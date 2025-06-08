from typing import List, Optional, Dict, Any
import pandas as pd
from datetime import datetime, timedelta
import pytz
from dateutil import parser
from repository.commodities import CommoditiesRepository

class CommoditiesService:
    def __init__(self):
        self.data_repo = CommoditiesRepository()
        self.cache = {}
    
    def _parse_datetime_with_tz(self, dt_str):
        dt = parser.isoparse(dt_str)
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        return dt.astimezone(pytz.UTC)
    
    def _ensure_timezone_aware(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return df
        try:
            if df.index.tz is None:
                print(f"Converting timezone-naive index to UTC")
                df.index = df.index.tz_localize('UTC')
            else:
                print(f"DataFrame already has timezone: {df.index.tz}")
        except Exception as e:
            print(f"Error making DataFrame timezone-aware: {e}")
            try:
                df.index = pd.to_datetime(df.index).tz_localize('UTC')
            except:
                print("Failed to localize timezone, keeping as-is")
        return df

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
            df = self._ensure_timezone_aware(df)
            return self._format_ohlcv_response(df, symbol, timeframe)
        except Exception as e:
            print(f"Error in get_symbol_ohlcv service: {e}")
            return None

    async def get_symbol_data_range(self, symbol: str, start_date: str, end_date: str, timeframe: str = '1h') -> Optional[Dict[str, Any]]:
        try:
            start_dt = self._parse_datetime_with_tz(start_date)
            end_dt = self._parse_datetime_with_tz(end_date)
            start_date_str = start_dt.strftime('%Y-%m-%d')
            end_date_str = end_dt.strftime('%Y-%m-%d')
            df = self.data_repo.get_symbol_data_range(symbol, start_date_str, end_date_str, timeframe)
            if df is None:
                return None
            df = self._ensure_timezone_aware(df)
            if start_dt.hour != 0 or start_dt.minute != 0 or start_dt.second != 0:
                df = df[df.index >= start_dt]
            if end_dt.hour != 23 or end_dt.minute != 59:
                df = df[df.index <= end_dt]
            return self._format_ohlcv_response(df, symbol, timeframe)
        except Exception as e:
            print(f"Error in get_symbol_data_range service: {e}")
            return None

    async def get_replay_data_stream(self, symbol: str, timeframe: str = '1h', start_date: Optional[str] = None):
        try:
            if start_date:
                start_dt = self._parse_datetime_with_tz(start_date)

                df = self.data_repo.get_symbol_data_range(symbol=symbol, start_date=str(start_dt), end_date=None, timeframe=timeframe)
            else:
                df = self.data_repo.get_symbol_data(symbol, timeframe)

            if df is None or df.empty:
                print(f"No data found for {symbol}")
                return

            if df.index.tz is None:
                df.index = df.index.tz_localize('UTC')
            else:
                df.index = df.index.tz_convert('UTC')

            if start_date:
                df = df[df.index >= start_dt]

            if df.empty:
                print(f"No data available from {start_date} for {symbol}")
                return

            for timestamp, row in df.iterrows():
                bar_data = {
                    'timestamp': timestamp.isoformat(),
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': float(row.get('volume', 0))
                }
                yield bar_data

        except Exception as e:
            print(f"Error in replay stream for {symbol}: {e}")
            import traceback
            traceback.print_exc()
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
            df = self._ensure_timezone_aware(df)
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
                    'close': float(row['close']),
                    'volume': float(row.get('volume', 0))
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
