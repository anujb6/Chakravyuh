# backend/repository/data_repository.py

import pandas as pd
import os
from typing import List, Optional, Dict, Any
import glob

class CommoditiesRepository:
    def __init__(self, data_path: str = r"../data"):
        self.data_path = data_path
        self.timeframe_multipliers = {
           '1h': 1,
            '2h': 2, 
            '4h': 4,
            '1d': 24,
            '1w': 168,
            '1mo': 720
        }
    
    def get_available_symbols(self) -> List[str]:
        try:
            csv_files = glob.glob(os.path.join(self.data_path, "*", "*_1h.csv"))
            symbols = []
            
            for file_path in csv_files:
                filename = os.path.basename(file_path)
                symbol = filename.replace("_1h.csv", "")
                symbols.append(symbol.upper())
            
            return sorted(list(set(symbols)))
        except Exception as e:
            print(f"Error getting symbols: {e}")
            return []
    
    def get_symbol_data(self, symbol: str, timeframe: str = '1h') -> Optional[pd.DataFrame]:
        try:
            symbol_lower = symbol.lower()
            file_path = os.path.join(self.data_path, symbol_lower, f"{symbol_lower}_1h.csv")

            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                return None
            
            df = pd.read_csv(file_path)        
            df['time'] = pd.to_datetime(df['time'])
            df.set_index('time', inplace=True)
            
            if timeframe != '1h':
                df = self._resample_timeframe(df, timeframe)
            
            numeric_columns = ['open', 'high', 'low', 'close']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df.dropna()
            
        except Exception as e:
            print(f"Error loading data for {symbol}: {e}")
            return None
    
    def get_symbol_data_range(self, symbol: str, start_date: str, end_date: str, timeframe: str = '1h') -> Optional[pd.DataFrame]:
        try:
            df = self.get_symbol_data(symbol, timeframe)
            if df is None:
                return None
            
            start = pd.to_datetime(start_date)

            if end_date == None:
                end = df.index.max().tz_convert('UTC')
            else:
                end = pd.to_datetime(end_date)
            
            filtered_df = df.loc[start:end]
            print(filtered_df.head())
            return filtered_df
            
        except Exception as e:
            print(f"Error getting data range for {symbol}: {e}")
            return None
    
    def _resample_timeframe(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        if timeframe not in self.timeframe_multipliers:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        
        hours = self.timeframe_multipliers[timeframe]
        
        resampled = df.resample(f'{hours}H').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min', 
            'close': 'last'
        }).dropna()
        
        return resampled
    
    def get_latest_data(self, symbol: str, limit: int = 100, timeframe: str = '1h') -> Optional[pd.DataFrame]:
        try:
            df = self.get_symbol_data(symbol, timeframe)
            if df is None:
                return None
            
            return df.tail(limit)
            
        except Exception as e:
            print(f"Error getting latest data for {symbol}: {e}")
            return None
    
    def validate_symbol_exists(self, symbol: str) -> bool:
        symbol_lower = symbol.lower()
        file_path = os.path.join(self.data_path, symbol_lower, f"{symbol_lower}_1h.csv")
        return os.path.exists(file_path)
    
    def get_data_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            df = self.get_symbol_data(symbol, '1h')
            if df is None:
                return None
            
            return {
                'symbol': symbol.upper(),
                'total_bars': len(df),
                'date_range': {
                    'start': df.index.min().isoformat(),
                    'end': df.index.max().isoformat()
                },
                'last_price': float(df['close'].iloc[-1]),
                'available_timeframes': list(self.timeframe_multipliers.keys())
            }
            
        except Exception as e:
            print(f"Error getting data info for {symbol}: {e}")
            return None