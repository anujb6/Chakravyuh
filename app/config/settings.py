import os
from typing import Dict, Any

class Settings:
    def __init__(self):
        self.api_base_url = os.getenv('API_BASE_URL', 'http://localhost:8000/commodities')
        self.default_timeframe = '1D'
        self.default_symbol = 'GOLD'
        self.chart_theme = 'dark'
        self.window_geometry = (1200, 800)
        self.update_interval = 5000  # milliseconds
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            'api_base_url': self.api_base_url,
            'default_timeframe': self.default_timeframe,
            'default_symbol': self.default_symbol,
            'chart_theme': self.chart_theme,
            'window_geometry': self.window_geometry,
            'update_interval': self.update_interval
        }

settings = Settings()