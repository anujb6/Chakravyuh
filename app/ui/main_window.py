import sys
from PyQt5.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                             QSplitter, QStatusBar, QMenuBar, QAction, QMessageBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon
from lightweight_charts.widgets import QtChart
from config.settings import settings
from services.api_client import APIClient
import logging
from ui.widgets.chart_widget import ChartWidget

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
        self.chart_widget.data_reload_requested.connect(self.reload_symbol_data)
        
    def setup_ui(self):
        self.setWindowTitle("Commodities Trading Dashboard")
        self.setGeometry(100, 100, *settings.window_geometry)
        
        # Central widget - now just the chart widget
        self.chart_widget = ChartWidget()
        self.setCentralWidget(self.chart_widget)
        
    def setup_statusbar(self):
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Ready")
        
    def setup_connections(self):
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.start(settings.update_interval)
        
    def setup_chart_topbar(self):
        """Setup the chart's topbar with symbol menu, timeframe selector and refresh button"""
        chart = self.chart_widget.chart
        
        # Add symbol menu (left side)
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
            
        # Add timeframe switcher (left side, after symbol)
        if self.available_timeframes:
            chart.topbar.switcher(
                name='timeframe',
                options=tuple(self.available_timeframes),
                default='1h' if '1h' in self.available_timeframes else self.available_timeframes[0],
                align='left',
                func=self.on_timeframe_changed
            )          
    
    def reload_symbol_data(self, symbol: str, timeframe: str):
        """Handle data reload request from chart widget"""
        try:
            self.statusbar.showMessage(f"Reloading data for {symbol} - {timeframe}...")            
            # If you have an API client instance:
            market_data = self.api_client.get_symbol_data(symbol=symbol, timeframe=timeframe)
            self.chart_widget.set_data(market_data)
            
            print(f"Reloading data for {symbol} - {timeframe}")
            
        except Exception as e:
            logger.exception(f"Error reloading data for {symbol}")
            self.chart_widget.status_label.setText(f"Error reloading data: {e}")
    
    def load_initial_data(self):
        try:
            self.statusbar.showMessage("Loading symbols...")
            self.available_symbols = self.api_client.get_available_symbols()
            
            timeframes = self.api_client.get_supported_timeframes()
            self.available_timeframes = timeframes["timeframes"]
            
            # Setup chart topbar after we have symbols and timeframes
            self.setup_chart_topbar()
            
            # Load data for the first symbol by default
            if self.available_symbols:
                first_symbol = self.available_symbols[0].symbol
                self.load_symbol_data(first_symbol)
            
            self.statusbar.showMessage("Ready")
        except Exception as e:
            self.statusbar.showMessage(f"Error loading data: {e}")
            
    def on_symbol_changed(self, menu_widget: QtChart):
        """Called when symbol menu selection is changed"""
        print(menu_widget.topbar._widgets['symbol'].__dict__, menu_widget.topbar._widgets['symbol'].value)
        selected_symbol = menu_widget.topbar._widgets['symbol'].value
        self.load_symbol_data(selected_symbol)
            
    def on_timeframe_changed(self, timeframe_widget):
        """Called when timeframe switcher is changed"""
        if self.current_symbol:
            self.load_symbol_data(self.current_symbol)
            
    def load_symbol_data(self, symbol: str):
        """Load data for the specified symbol"""
        try:
            self.statusbar.showMessage(f"Loading data for {symbol}...")
            self.current_symbol = symbol

            # Get current timeframe from topbar
            timeframe = self.chart_widget.chart.topbar['timeframe'].value
            print(f"Loading data for {symbol} with timeframe {timeframe}")
                
            data = self.api_client.get_symbol_data(symbol, timeframe)
            if data:
                self.chart_widget.set_data(data)
                
            self.statusbar.showMessage(f"Loaded {symbol}")
            
        except Exception as e:
            self.statusbar.showMessage(f"Error loading {symbol}: {e}")
            
    def refresh_data(self, button_widget=None):
        """Called when refresh button is clicked"""
        if self.current_symbol:
            self.load_symbol_data(self.current_symbol)
        
    def get_current_symbol(self) -> str:
        """Get the currently selected symbol"""
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