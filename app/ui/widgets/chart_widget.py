# File: ui/widgets/chart_widget.py
import pandas as pd
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PyQt5.QtCore import Qt
from lightweight_charts.widgets import QtChart
from services.api_client import MarketDataResponse


class ChartWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Chart title
        self.title_label = QLabel("Select a symbol to view chart")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
        layout.addWidget(self.title_label)
        
        # Chart
        self.chart = QtChart(self, toolbox=True)
        webview = self.chart.get_webview()
        self.setMinimumSize(600, 400)
        webview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(webview)
        
    def set_data(self, data: MarketDataResponse):
        try:
            # Convert API data to DataFrame
            df_data = []
            for bar in data.data:
                df_data.append({
                    'time': bar.time,
                    'open': bar.open,
                    'high': bar.high,
                    'low': bar.low,
                    'close': bar.close
                })
                
            df = pd.DataFrame(df_data)
            
            # Convert time column to datetime if needed
            if not df.empty:
                df['time'] = pd.to_datetime(df['time'])
                
                # Set chart data
                self.chart.set(df)
                
                # Update title
                self.title_label.setText(f"{data.symbol} - {data.timeframe}")
                
        except Exception as e:
            print(f"Error setting chart data: {e}")