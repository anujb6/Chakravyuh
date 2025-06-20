from PyQt5.QtWidgets import (QMainWindow, QStatusBar, QMessageBox)
from PyQt5.QtCore import  QTimer
from lightweight_charts.widgets import QtChart
from config.settings import settings
from services.api_client import APIClient
import logging
from ui.widgets.chart_widget import ChartWidget
import pandas as pd

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.api_client = APIClient(settings.api_base_url)
        self.available_timeframes = []
        self.available_symbols = []
        self.current_symbol = None
        self.setup_ui()
        self.setup_statusbar()
        self.setup_connections()
        self.load_initial_data()
        
    def setup_ui(self):
        self.setWindowTitle("Commodities Trading Dashboard")
        self.setGeometry(100, 100, *settings.window_geometry)
        
        self.chart_widget = ChartWidget()
        self.setCentralWidget(self.chart_widget)
        
    def setup_statusbar(self):
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Ready")
        
    def setup_connections(self):
        self.refresh_timer = QTimer()
        self.refresh_timer.start(settings.update_interval)
        
        self.chart_widget.data_reload_requested.connect(self.reload_symbol_data)
        
    def setup_chart_topbar(self):
        chart = self.chart_widget.chart
        
        if self.available_symbols:
            symbol_options = tuple(symbol.symbol for symbol in self.available_symbols)
            default_symbol = symbol_options[0] if symbol_options else ""
            
            chart.topbar.menu(
                name='symbol',
                options=symbol_options,
                default=default_symbol,
                align='left',
                func=self.on_symbol_changed
            )
            
        if self.available_timeframes:
            chart.topbar.switcher(
                name='timeframe',
                options=tuple(self.available_timeframes),
                default='1h' if '1h' in self.available_timeframes else self.available_timeframes[0],
                align='left',
                func=self.on_timeframe_changed
            )          
    
    def reload_symbol_data(self, symbol: str, timeframe: str):
        try:
            self.statusbar.showMessage(f"Reloading data for {symbol} - {timeframe}...")            
            market_data = self.api_client.get_symbol_data(symbol=symbol, timeframe=timeframe)
            self.chart_widget.set_data(market_data)
            self.statusbar.showMessage("Data reloaded")
            
        except Exception as e:
            logger.exception(f"Error reloading data for {symbol}")
            self.chart_widget.status_label.setText(f"Error reloading data: {e}")
            self.statusbar.showMessage(f"Error reloading data: {e}")
    
    def load_historical_data(self, symbol: str, timeframe: str, start_date: str, end_date: str):
        try:
            self.statusbar.showMessage(f"Loading historical data for {symbol}...")
            start_date = pd.to_datetime(start_date).tz_localize('UTC')
            end_date = pd.to_datetime(end_date).tz_localize('UTC') if end_date else None

            historical_data = self.api_client.get_symbol_data_range(
                symbol=symbol, 
                timeframe=timeframe,
                start=start_date,
                end=end_date
            )
            
            if historical_data:
                self.chart_widget.set_historical_data(historical_data)
                self.statusbar.showMessage(f"Historical data loaded ({len(historical_data.data)} bars)")
            else:
                self.statusbar.showMessage("No historical data found")
                
        except Exception as e:
            logger.exception(f"Error loading historical data for {symbol}")
            self.statusbar.showMessage(f"Error loading historical data: {e}")
    
    def load_initial_data(self):
        try:
            self.statusbar.showMessage("Loading symbols...")
            self.available_symbols = self.api_client.get_available_symbols()
            
            timeframes = self.api_client.get_supported_timeframes()
            self.available_timeframes = timeframes["timeframes"]

            self.setup_chart_topbar()
            
            if self.available_symbols:
                first_symbol = self.available_symbols[0].symbol
                self.load_symbol_data(first_symbol)
            
            self.statusbar.showMessage("Ready")
        except Exception as e:
            self.statusbar.showMessage(f"Error loading data: {e}")
            
    def on_symbol_changed(self, menu_widget: QtChart):
        selected_symbol = menu_widget.topbar._widgets['symbol'].value
        self.load_symbol_data(selected_symbol)
            
    def on_timeframe_changed(self, timeframe_widget):
        if self.current_symbol:
            self.load_symbol_data(self.current_symbol)
            
    def load_symbol_data(self, symbol: str):
        try:
            self.statusbar.showMessage(f"Loading data for {symbol}...")
            self.current_symbol = symbol

            timeframe = self.chart_widget.chart.topbar['timeframe'].value
                
            data = self.api_client.get_symbol_data(symbol, timeframe)

            if data:
                self.chart_widget.set_data(data)
                
            self.statusbar.showMessage(f"Loaded {symbol}")
            
        except Exception as e:
            self.statusbar.showMessage(f"Error loading {symbol}: {e}")
            
    def refresh_data(self, button_widget=None):
        if self.current_symbol:
            self.load_symbol_data(self.current_symbol)
        
    def get_current_symbol(self) -> str:
        return self.current_symbol or ""
                
    def show_settings(self):
        QMessageBox.information(self, "Settings", "Settings dialog not implemented yet")
        
    def show_about(self):
        QMessageBox.about(self, "About", 
                         "Commodities Trading Dashboard\n\n"
                         "A professional trading interface for commodities market data.\n"
                         "Built with PyQt5 and lightweight-charts.")
                         
    def closeEvent(self, event):
        self.api_client.close()
        event.accept()