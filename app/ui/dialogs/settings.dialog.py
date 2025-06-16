from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QSpinBox, QComboBox, QPushButton,
                             QFormLayout, QGroupBox, QDialogButtonBox)
from PyQt5.QtCore import Qt
from config.settings import settings

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(400, 300)
        self.setup_ui()
        self.load_settings()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # API Settings Group
        api_group = QGroupBox("API Settings")
        api_layout = QFormLayout(api_group)
        
        self.api_url_edit = QLineEdit()
        api_layout.addRow("API Base URL:", self.api_url_edit)
        
        layout.addWidget(api_group)
        
        # Chart Settings Group
        chart_group = QGroupBox("Chart Settings")
        chart_layout = QFormLayout(chart_group)
        
        self.default_timeframe_combo = QComboBox()
        self.default_timeframe_combo.addItems(['1m', '5m', '15m', '30m', '1h', '4h', '1D', '1W'])
        chart_layout.addRow("Default Timeframe:", self.default_timeframe_combo)
        
        self.default_symbol_edit = QLineEdit()
        chart_layout.addRow("Default Symbol:", self.default_symbol_edit)
        
        layout.addWidget(chart_group)
        
        # Update Settings Group
        update_group = QGroupBox("Update Settings")
        update_layout = QFormLayout(update_group)
        
        self.update_interval_spin = QSpinBox()
        self.update_interval_spin.setRange(1000, 60000)
        self.update_interval_spin.setSuffix(" ms")
        update_layout.addRow("Auto-refresh Interval:", self.update_interval_spin)
        
        layout.addWidget(update_group)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def load_settings(self):
        self.api_url_edit.setText(settings.api_base_url)
        self.default_timeframe_combo.setCurrentText(settings.default_timeframe)
        self.default_symbol_edit.setText(settings.default_symbol)
        self.update_interval_spin.setValue(settings.update_interval)
        
    def accept(self):
        # Save settings
        settings.api_base_url = self.api_url_edit.text()
        settings.default_timeframe = self.default_timeframe_combo.currentText()
        settings.default_symbol = self.default_symbol_edit.text()
        settings.update_interval = self.update_interval_spin.value()
        
        super().accept()