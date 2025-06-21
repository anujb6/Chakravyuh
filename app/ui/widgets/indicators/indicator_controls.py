import talib
import pandas as pd
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import (QPushButton, QHBoxLayout, QLabel,
                             QDialog, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
                             QWidget, QFrame, QScrollArea)
from PyQt5.QtCore import pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QFont
from lightweight_charts.widgets import QtChart
from PyQt5.QtWidgets import QApplication

from ui.widgets.indicators.indicator_popup import IndicatorPopup
from ui.widgets.indicators.applied_indicators_list import AppliedIndicatorsList
from manager.indicator_manager import IndicatorManager

class IndicatorControls(QObject):
    indicator_added = pyqtSignal(str)
    indicator_removed = pyqtSignal(str)

    def __init__(self, parent_layout, parent_widget=None):
        super().__init__()
        self.manager = None
        self.popup = None
        self.applied_list = None
        self.parent_widget = parent_widget
        self.setup_ui(parent_layout)

    def set_manager(self, manager: IndicatorManager):
        self.manager = manager
        if self.popup:
            self.popup.set_manager(manager)
        if self.applied_list:
            self.applied_list.set_manager(manager)

    def setup_ui(self, parent_layout):
        self.indicators_btn = QPushButton("📊 Indicators")
        self.indicators_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
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
        self.indicators_btn.clicked.connect(self.show_indicator_popup)
        parent_layout.addWidget(self.indicators_btn)

        self.applied_list = AppliedIndicatorsList(self.parent_widget or self.indicators_btn)
        self.applied_list.setWindowFlags(Qt.Popup)
        self.applied_list.indicator_removed.connect(self.indicator_removed.emit)

        self.show_applied_btn = QPushButton("📄 applied")
        self.show_applied_btn.setStyleSheet("""
            QPushButton {
                background-color: #2c2c2c ;
                border: 1px solid #CCC;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 11px;
            }
        """)
        self.show_applied_btn.clicked.connect(self.toggle_applied_list)
        parent_layout.addWidget(self.show_applied_btn)

    def show_indicator_popup(self):
        if not self.popup:
            self.popup = IndicatorPopup()
            self.popup.set_manager(self.manager)
            self.popup.indicator_added.connect(self.on_indicator_added)

        self.popup.exec_()

    def on_indicator_added(self, name):
        self.indicator_added.emit(name)
        if self.applied_list:
            self.applied_list.refresh_list()

    def toggle_applied_list(self):
        if self.applied_list.isVisible():
            self.applied_list.hide()
            return

        btn_rect = self.show_applied_btn.rect()
        global_pos = self.show_applied_btn.mapToGlobal(btn_rect.bottomLeft())

        screen = QApplication.primaryScreen()
        screen_geom = screen.availableGeometry()
        screen_width = screen_geom.width()

        popup_width = self.applied_list.sizeHint().width() or 250

        x = global_pos.x()
        if x + popup_width > screen_width:
            x = screen_width - popup_width - 20

        y = global_pos.y()
        self.applied_list.move(x, y)
        self.applied_list.refresh_list()
        self.applied_list.show()

    def clear_indicators(self):
        if self.manager:
            self.manager.clear_all()
        if self.applied_list:
            self.applied_list.refresh_list()
