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

class IndicatorManager:
    def __init__(self, chart: QtChart):
        self.chart = chart
        self.indicators = {}
        self.data = None
    
    def clear_all(self):
        for name in list(self.indicators.keys()):
            self.remove_indicator(name)

    def set_data(self, data: pd.DataFrame):
        self.data = data.copy(deep=True)
        if not self.data.empty:
            if not pd.api.types.is_datetime64_any_dtype(self.data['time']):
                self.data['time'] = pd.to_datetime(self.data['time'])
            
            if self.data['time'].dt.tz is not None:
                self.data['time'] = self.data['time'].dt.tz_localize(None)
        self.recalculate_all()
    
    def update_data(self, series: pd.Series):
        if self.data is not None:
            series_time = series['time']
            
            if pd.api.types.is_datetime64_any_dtype(series_time):
                if hasattr(series_time, 'tz_localize') and series_time.tz is not None:
                    series_time = series_time.tz_localize(None)
            else:
                series_time = pd.to_datetime(series_time)
                if series_time.tz is not None:
                    series_time = series_time.tz_localize(None)
            
            new_row = pd.DataFrame([{
                'time': series_time,
                'open': series['open'],
                'high': series['high'],
                'low': series['low'],
                'close': series['close']
            }])
            
            if series_time in self.data['time'].values:
                self.data = self.data[self.data['time'] != series_time].copy()
            self.data = pd.concat([self.data, new_row], ignore_index=True)
            self.data = self.data.sort_values('time').reset_index(drop=True)
            
            for name, indicator in self.indicators.items():
                if indicator['type'] == 'bollinger_bands':
                    self._update_bollinger_bands_full(name, indicator)
        
        self.recalculate_all()

    def remove_indicator(self, name: str):
        print(f"removing indicator {name}")
        if name in self.indicators:
            try:
                for line in self.indicators[name]['lines']:
                    try:
                       line.set(None)
                    except Exception as e:
                        print(f"Error deleting line: {e}")
            finally:
                del self.indicators[name]

    def recalculate_all(self):
        if self.data is None or self.data.empty:
            return
        for name, indicator in list(self.indicators.items()):
            if indicator['type'] == 'bollinger_bands':
                self._update_bollinger_bands_full(name, indicator)

    def _update_bollinger_bands_full(self, name: str, indicator: dict):
        if self.data is None or len(self.data) < 2:
            return
            
        params = indicator['params']
        period = params['period']
        std_dev = params['std_dev']
        
        if len(self.data) < period:
            return
            
        closes = self.data['close'].values
        upper, middle, lower = talib.BBANDS(closes, timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev)
        
        times = self.data['time']
        bb_data = pd.DataFrame({
            'time': times,
            'upper': upper,
            'middle': middle,
            'lower': lower
        }).dropna()
        
        indicator['lines'][0].set(bb_data[['time', 'upper']].rename(columns={'upper': 'value'}))
        indicator['lines'][1].set(bb_data[['time', 'middle']].rename(columns={'middle': 'value'}))
        indicator['lines'][2].set(bb_data[['time', 'lower']].rename(columns={'lower': 'value'}))
        
        indicator['data'] = bb_data

    def add_bollinger_bands(self, period=20, std_dev=2, name=None):
        if name is None:
            name = f"Bollinger Bands ({period}, {std_dev})"
            
        if self.data is None or len(self.data) < period:
            return None
            
        closes = self.data['close'].values
        upper, middle, lower = talib.BBANDS(closes, timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev)
        
        times = self.data['time']
        bb_data = pd.DataFrame({
            'time': times,
            'upper': upper,
            'middle': middle, 
            'lower': lower
        }).dropna()

        upper_line = self.chart.create_line(color='rgba(255, 0, 0, 0.7)', style='solid', width=1, price_line=False, price_label=False)
        middle_line = self.chart.create_line(color='rgba(0, 0, 255, 0.7)', style='dashed', width=1, price_line=False, price_label=False)
        lower_line = self.chart.create_line(color='rgba(255, 0, 0, 0.7)', style='solid', width=1, price_line=False, price_label=False)
        
        upper_line.set(bb_data[['time', 'upper']].rename(columns={'upper': 'value'}))
        middle_line.set(bb_data[['time', 'middle']].rename(columns={'middle': 'value'}))
        lower_line.set(bb_data[['time', 'lower']].rename(columns={'lower': 'value'}))
        
        self.indicators[name] = {
            'type': 'bollinger_bands',
            'lines': [upper_line, middle_line, lower_line],
            'params': {'period': period, 'std_dev': std_dev},
            'data': bb_data
        }
        
        return name

    def get_applied_indicators(self):
        return list(self.indicators.keys())

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

class AppliedIndicatorsList(QFrame):
    indicator_removed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = None
        self.setup_ui()
        self.setWindowFlags(Qt.Popup)
        self.setFrameShape(QFrame.Box)
        self.setStyleSheet("background-color: #1e1e1e; border: 1px solid #444;")

        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_list)
        self.refresh_timer.start(1000)

    def set_manager(self, manager: IndicatorManager):
        self.manager = manager
        self.refresh_list()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title_label = QLabel("Applied Indicators")
        title_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        title_label.setStyleSheet("color: #e0e0e0;")
        layout.addWidget(title_label)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.setStyleSheet("""
            QLineEdit {
                padding: 6px 10px;
                background-color: #2c2c2c;
                border: 1px solid #555;
                color: white;
                border-radius: 4px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #2979FF;
            }
        """)
        self.search_bar.textChanged.connect(self.show_dropdown)
        layout.addWidget(self.search_bar)

        self.dropdown = QListWidget(self)
        self.dropdown.setWindowFlags(Qt.Popup)
        self.dropdown.setFont(QFont("Segoe UI", 10))
        self.dropdown.setStyleSheet("""
            QListWidget {
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #555;
                padding: 4px;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 6px 12px;
                font-size: 12px;
            }
            QListWidget::item:hover {
                background-color: #2979FF;
            }
        """)
        self.dropdown.hide()
        self.dropdown.itemClicked.connect(self.on_dropdown_item_clicked)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setMaximumHeight(150)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

        self.indicators_widget = QWidget()
        self.indicators_layout = QVBoxLayout(self.indicators_widget)
        self.indicators_layout.setContentsMargins(0, 0, 0, 0)
        self.indicators_layout.setSpacing(4)

        scroll_area.setWidget(self.indicators_widget)
        layout.addWidget(scroll_area)

    def show_dropdown(self, text):
        if not self.manager:
            return

        indicators = self.manager.get_applied_indicators()
        self.dropdown.clear()

        if not text.strip():
            self.dropdown.hide()
            return

        matches = [i for i in indicators if text.lower() in i.lower()]
        if not matches:
            self.dropdown.hide()
            return

        for name in matches:
            self.dropdown.addItem(name)

        row_height = self.dropdown.sizeHintForRow(0) or 24
        height = row_height * min(5, len(matches)) + 4
        pos = self.search_bar.mapToGlobal(self.search_bar.rect().bottomLeft())

        self.dropdown.setGeometry(pos.x(), pos.y(), self.search_bar.width(), height)
        self.dropdown.raise_()
        self.dropdown.show()
        self.dropdown.setFocus()

    def on_dropdown_item_clicked(self, item):
        name = item.text()
        self.dropdown.hide()

        for i in range(self.indicators_layout.count()):
            widget = self.indicators_layout.itemAt(i).widget()
            if widget:
                label = widget.findChild(QLabel)
                if label and label.text() == name:
                    widget.setStyleSheet(widget.styleSheet() + "border: 1px solid #2979FF;")

    def focusOutEvent(self, event):
        if not self.dropdown.underMouse():
            self.dropdown.hide()
        super().focusOutEvent(event)

    def refresh_list(self):
        if not self.manager:
            return

        for i in reversed(range(self.indicators_layout.count())):
            widget = self.indicators_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        indicators = self.manager.get_applied_indicators()
        if not indicators:
            label = QLabel("No indicators applied")
            label.setStyleSheet("color: #888; font-style: italic; padding: 10px;")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.indicators_layout.addWidget(label)
        else:
            for name in indicators:
                self.indicators_layout.addWidget(self.create_indicator_item(name))

        self.indicators_layout.addStretch()

    def create_indicator_item(self, name):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #2e2e2e;
                border: 1px solid #444;
                border-radius: 4px;
            }
            QFrame:hover {
                background-color: #3a3a3a;
            }
        """)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(8, 6, 8, 6)

        label = QLabel(name)
        label.setStyleSheet("color: white; font-size: 12px;")
        layout.addWidget(label)

        layout.addStretch()

        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(20, 20)
        remove_btn.setToolTip("Remove indicator")
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #e53935;
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #c62828;
            }
        """)
        remove_btn.clicked.connect(lambda checked=False, n=name: self.remove_indicator(n))
        layout.addWidget(remove_btn)

        return frame

    def remove_indicator(self, name):
        if self.manager:
            print(f"Removing: {name}")
            self.manager.remove_indicator(name)
            self.indicator_removed.emit(name)
            self.refresh_list()

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
