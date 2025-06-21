from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (QPushButton, QHBoxLayout, QLabel,
                             QDialog, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont

from manager.indicator_manager import IndicatorManager

class IndicatorPopup(QDialog):
    indicator_added = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = None
        self.available_indicators = [
            "Bollinger Bands"
        ]
        self.setup_ui()
        
    def set_manager(self, manager: IndicatorManager):
        self.manager = manager
        
    def setup_ui(self):
        self.setWindowTitle("Add Indicators")
        self.setFixedSize(400, 500)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title_label = QLabel("Select Indicators")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search indicators...")
        self.search_bar.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border: 2px solid #444;
                border-radius: 6px;
                font-size: 12px;
                background-color: #121212;
                color: #E0E0E0;
            }
            QLineEdit:focus {
                border-color: #2979FF;
                background-color: #1E1E1E;
            }
            QLineEdit::placeholder {
                color: #888;
            }
        """)
        self.search_bar.textChanged.connect(self.filter_indicators)
        layout.addWidget(self.search_bar)

        self.indicators_list = QListWidget()
        self.indicators_list.setStyleSheet("""
            QListWidget {
                background-color: #121212;
                border: 1px solid #333;
                border-radius: 6px;
                color: #E0E0E0;
            }
            QListWidget::item {
                padding: 12px 15px;
                border-bottom: 1px solid #2c2c2c;
                font-size: 12px;
                color: #E0E0E0;
            }
            QListWidget::item:hover {
                background-color: #1f1f1f;
                color: #ffffff;
            }
            QListWidget::item:selected {
                background-color: #2979FF;
                color: #ffffff;
            }
        """)

        self.indicators_list.itemDoubleClicked.connect(self.add_selected_indicator)
        layout.addWidget(self.indicators_list)
        
        self.populate_indicators_list()
        
        button_layout = QHBoxLayout()
        
        add_button = QPushButton("Add Selected")
        add_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        add_button.clicked.connect(self.add_selected_indicator)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5;
                color: #333;
                border: 1px solid #ddd;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(add_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
    def populate_indicators_list(self):
        self.indicators_list.clear()
        for indicator in self.available_indicators:
            item = QListWidgetItem(indicator)
            self.indicators_list.addItem(item)
            
    def filter_indicators(self, text):
        for i in range(self.indicators_list.count()):
            item = self.indicators_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())
            
    def add_selected_indicator(self):
        current_item = self.indicators_list.currentItem()
        if current_item and self.manager:
            indicator_name = current_item.text()
            
            if indicator_name == "Bollinger Bands":
                result = self.manager.add_bollinger_bands(period=20, std_dev=2)
                if result:
                    self.indicator_added.emit(result)
                    self.accept()