import sys
from PyQt5.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                             QSplitter, QStatusBar, QMenuBar, QAction, QMessageBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon

from config.settings import settings
from services.api_client import APIClient
from ui.widgets.chart_widget import ChartWidget
from ui.widgets.symbol_list import SymbolListWidget
from ui.widgets.data_panel import DataPanelWidget
from ui.widgets.toolbar import ToolbarWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.api_client = APIClient(settings.api_base_url)
        self.setup_ui()
        self.setup_menu()
        self.setup_statusbar()
        self.setup_connections()
        self.load_initial_data()
        
    def setup_ui(self):
        self.setWindowTitle("Commodities Trading Dashboard")
        self.setGeometry(100, 100, *settings.window_geometry)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Create main splitter
        main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(main_splitter)
        
        # Left panel (symbol list and data)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)
        
        # Toolbar
        self.toolbar = ToolbarWidget()
        left_layout.addWidget(self.toolbar)
        
        # Symbol list
        self.symbol_list = SymbolListWidget()
        left_layout.addWidget(self.symbol_list)
        
        # Data panel
        self.data_panel = DataPanelWidget()
        left_layout.addWidget(self.data_panel)
        
        # Chart widget
        self.chart_widget = ChartWidget()
        
        # Add to splitter
        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(self.chart_widget)
        
        # Set splitter sizes (20% left, 80% right)
        main_splitter.setSizes([240, 960])
        
    def setup_menu(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        refresh_action = QAction('Refresh Data', self)
        refresh_action.setShortcut('F5')
        refresh_action.triggered.connect(self.refresh_data)
        file_menu.addAction(refresh_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu('View')
        
        # Tools menu
        tools_menu = menubar.addMenu('Tools')
        
        settings_action = QAction('Settings', self)
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        
        about_action = QAction('About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def setup_statusbar(self):
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Ready")
        
    def setup_connections(self):
        # Symbol selection
        self.symbol_list.symbol_selected.connect(self.on_symbol_selected)
        
        # Toolbar connections
        self.toolbar.timeframe_changed.connect(self.on_timeframe_changed)
        self.toolbar.refresh_requested.connect(self.refresh_data)
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.auto_refresh)
        self.refresh_timer.start(settings.update_interval)
        
    def load_initial_data(self):
        try:
            self.statusbar.showMessage("Loading symbols...")
            symbols = self.api_client.get_available_symbols()
            self.symbol_list.set_symbols(symbols)
            
            timeframes = self.api_client.get_supported_timeframes()
            print(f"Available timeframes: {timeframes["timeframes"]}")
            self.toolbar.set_timeframes(timeframes = timeframes["timeframes"])
            
            self.statusbar.showMessage("Ready")
        except Exception as e:
            self.statusbar.showMessage(f"Error loading data: {e}")
            
    def on_symbol_selected(self, symbol: str):
        try:
            self.statusbar.showMessage(f"Loading data for {symbol}...")
            
            # Get current timeframe
            timeframe = self.toolbar.get_current_timeframe()
            
            print(f"Loading data for {symbol} with timeframe {timeframe}")
            
            # Load chart data
            data = self.api_client.get_symbol_data(symbol, timeframe)
            if data:
                self.chart_widget.set_data(data)
                
            # Load statistics
            stats = self.api_client.get_symbol_statistics(symbol)
            if stats:
                self.data_panel.set_stats(stats)
                
            self.statusbar.showMessage(f"Loaded {symbol}")
            
        except Exception as e:
            self.statusbar.showMessage(f"Error loading {symbol}: {e}")
            
    def on_timeframe_changed(self, timeframe: str):
        current_symbol = self.symbol_list.get_current_symbol()
        if current_symbol:
            self.on_symbol_selected(current_symbol)
            
    def refresh_data(self):
        current_symbol = self.symbol_list.get_current_symbol()
        if current_symbol:
            self.on_symbol_selected(current_symbol)
            
    def auto_refresh(self):
        # Only auto-refresh if we have a current symbol
        current_symbol = self.symbol_list.get_current_symbol()
        if current_symbol:
            try:
                # Just update statistics for auto-refresh
                stats = self.api_client.get_symbol_statistics(current_symbol)
                if stats:
                    self.data_panel.set_stats(stats)
            except Exception as e:
                pass  # Silently fail for auto-refresh
                
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