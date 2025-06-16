# File: ui/dialogs/about_dialog.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About")
        self.setModal(True)
        self.resize(400, 300)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Commodities Trading Dashboard")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Version
        version = QLabel("Version 1.0.0")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)
        
        # Description
        description = QTextEdit()
        description.setReadOnly(True)
        description.setMaximumHeight(150)
        description.setHtml("""
        <p>A professional desktop application for viewing and analyzing commodities market data.</p>
        
        <p><b>Features:</b></p>
        <ul>
            <li>Real-time market data visualization</li>
            <li>Interactive charting with lightweight-charts</li>
            <li>Symbol search and filtering</li>
            <li>Market statistics and indicators</li>
            <li>Modern dark theme interface</li>
        </ul>
        
        <p><b>Built with:</b> PyQt5, lightweight-charts, httpx, pandas</p>
        """)
        layout.addWidget(description)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
