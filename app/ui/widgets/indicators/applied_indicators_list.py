from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (QPushButton, QHBoxLayout, QLabel,QVBoxLayout, QLineEdit, QListWidget,
                             QWidget, QFrame, QScrollArea)
from PyQt5.QtCore import pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QFont


from manager.indicator_manager import IndicatorManager

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
            self.manager.remove_indicator(name)
            self.indicator_removed.emit(name)
            self.refresh_list()