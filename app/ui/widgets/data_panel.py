# File: ui/widgets/data_panel.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QFrame, QGridLayout,
                             QScrollArea)
from PyQt5.QtCore import Qt
from services.api_client import SymbolStats

class DataPanelWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Market Data")
        title.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(title)
        
        # Scroll area for data
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Data container
        self.data_container = QWidget()
        self.data_layout = QVBoxLayout(self.data_container)
        
        scroll.setWidget(self.data_container)
        layout.addWidget(scroll)
        
        # Initialize with empty state
        self.show_empty_state()
        
    def show_empty_state(self):
        self.clear_layout()
        empty_label = QLabel("Select a symbol to view data")
        empty_label.setAlignment(Qt.AlignCenter)
        empty_label.setStyleSheet("color: #666; font-style: italic;")
        self.data_layout.addWidget(empty_label)
        
    def clear_layout(self):
        while self.data_layout.count():
            child = self.data_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
    def set_stats(self, stats: SymbolStats):
        self.clear_layout()
        
        # Symbol info
        symbol_frame = self.create_info_frame("Symbol Information")
        symbol_layout = QGridLayout(symbol_frame)
        
        symbol_layout.addWidget(QLabel("Symbol:"), 0, 0)
        symbol_layout.addWidget(QLabel(stats.symbol), 0, 1)
        
        symbol_layout.addWidget(QLabel("Timeframe:"), 1, 0)
        symbol_layout.addWidget(QLabel(stats.timeframe), 1, 1)
        
        symbol_layout.addWidget(QLabel("Last Updated:"), 2, 0)
        symbol_layout.addWidget(QLabel(stats.last_updated), 2, 1)
        
        self.data_layout.addWidget(symbol_frame)
        
        # Price info
        price_frame = self.create_info_frame("Price Information")
        price_layout = QGridLayout(price_frame)
        
        price_layout.addWidget(QLabel("Current Price:"), 0, 0)
        price_label = QLabel(f"${stats.current_price:.2f}")
        price_label.setStyleSheet("font-weight: bold;")
        price_layout.addWidget(price_label, 0, 1)
        
        price_layout.addWidget(QLabel("24h Change:"), 1, 0)
        change_text = f"${stats.price_change:.2f} ({stats.price_change_percent:.2f}%)"
        change_label = QLabel(change_text)
        
        # Color code the change
        if stats.price_change > 0:
            change_label.setStyleSheet("color: #00ff00; font-weight: bold;")
        elif stats.price_change < 0:
            change_label.setStyleSheet("color: #ff0000; font-weight: bold;")
        else:
            change_label.setStyleSheet("color: #ffff00; font-weight: bold;")
            
        price_layout.addWidget(change_label, 1, 1)
        
        price_layout.addWidget(QLabel("24h High:"), 2, 0)
        high_label = QLabel(f"${stats.high_24h:.2f}")
        price_layout.addWidget(high_label, 2, 1)
        
        price_layout.addWidget(QLabel("24h Low:"), 3, 0)
        low_label = QLabel(f"${stats.low_24h:.2f}")
        price_layout.addWidget(low_label, 3, 1)
        
        self.data_layout.addWidget(price_frame)
        
        # Add stretch to push content to top
        self.data_layout.addStretch()
        
    def create_info_frame(self, title: str) -> QFrame:
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 5px;
                margin: 2px;
            }
        """)
        
        layout = QVBoxLayout(frame)
        
        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; color: #fff; padding: 5px;")
        layout.addWidget(title_label)
        
        return frame
