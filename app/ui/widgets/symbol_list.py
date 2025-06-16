# File: ui/widgets/symbol_list.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QListWidget, QListWidgetItem, 
                             QLabel, QLineEdit, QHBoxLayout)
from PyQt5.QtCore import Qt, pyqtSignal
from typing import List
from services.api_client import SymbolInfo

class SymbolListWidget(QWidget):
    symbol_selected = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.symbols = []
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Symbols")
        title.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(title)
        
        # Search box
        search_layout = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search symbols...")
        self.search_box.textChanged.connect(self.filter_symbols)
        search_layout.addWidget(self.search_box)
        layout.addLayout(search_layout)
        
        # Symbol list
        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        layout.addWidget(self.list_widget)
        
    def set_symbols(self, symbols: List[SymbolInfo]):
        self.symbols = symbols
        self.populate_list()
        
    def populate_list(self, filter_text: str = ""):
        self.list_widget.clear()
        
        for symbol in self.symbols:
            if filter_text.lower() in symbol.symbol.lower():
                item = QListWidgetItem(symbol.symbol)
                item.setData(Qt.UserRole, symbol)
                
                # Add tooltip with symbol info
                tooltip = (f"Symbol: {symbol.symbol}\n"
                          f"Last Price: {symbol.last_price}\n"
                          f"Total Bars: {symbol.total_bars}")
                item.setToolTip(tooltip)
                
                self.list_widget.addItem(item)
                
    def filter_symbols(self, text: str):
        self.populate_list(text)
        
    def on_item_clicked(self, item: QListWidgetItem):
        symbol_info = item.data(Qt.UserRole)
        self.symbol_selected.emit(symbol_info.symbol)
        
    def get_current_symbol(self) -> str:
        current_item = self.list_widget.currentItem()
        if current_item:
            symbol_info = current_item.data(Qt.UserRole)
            return symbol_info.symbol
        return ""
