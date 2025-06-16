# File: ui/widgets/toolbar.py
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QLabel, QComboBox, 
                             QPushButton, QSpacerItem, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon

class ToolbarWidget(QWidget):
    timeframe_changed = pyqtSignal(str)
    refresh_requested = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Timeframe selector
        tf_label = QLabel("Timeframe:")
        layout.addWidget(tf_label)
        
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.setMinimumWidth(80)
        self.timeframe_combo.currentTextChanged.connect(self.on_timeframe_changed)
        layout.addWidget(self.timeframe_combo)
        
        # Spacer
        spacer = QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        layout.addItem(spacer)
        
        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_requested.emit)
        layout.addWidget(self.refresh_btn)
        
    def set_timeframes(self, timeframes: list):
        self.timeframe_combo.clear()
        for tf in timeframes:
            self.timeframe_combo.addItem(tf)
            
        # Set default
        if timeframes:
            self.timeframe_combo.setCurrentText("1h")
            
    def get_current_timeframe(self) -> str:
        current_tf = self.timeframe_combo.currentText()
        print(f"Current timeframe: {current_tf}")
        return current_tf
        
    def on_timeframe_changed(self, timeframe: str):
        self.timeframe_changed.emit(timeframe)