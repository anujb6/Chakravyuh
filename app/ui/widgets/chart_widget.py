import logging
import pandas as pd
import asyncio
import websockets
import json
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider,
    QComboBox, QDateEdit, QSizePolicy, QSpacerItem
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QDate
from PyQt5.QtGui import QFont
from lightweight_charts.widgets import QtChart
from services.api_client import MarketDataResponse

# Configure module-level logger
logger = logging.getLogger(__name__)


class WebSocketThread(QThread):
    """Thread to handle WebSocket connection for replay data"""
    data_received = pyqtSignal(dict)
    connection_status = pyqtSignal(str)

    def __init__(self, symbol, ws_url="ws://localhost:8000"):
        super().__init__()
        self.symbol = symbol
        self.ws_url = ws_url
        self.websocket = None
        self.running = False
        self.loop = None
        self._stop_event = asyncio.Event()

    def run(self):
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.connect_and_listen())
        except RuntimeError as e:
            if "Event loop stopped" not in str(e):
                logger.exception("WebSocket thread runtime error")
        except Exception as e:
            logger.exception("WebSocket thread error")
        finally:
            if self.loop and not self.loop.is_closed():
                self.loop.close()

    async def connect_and_listen(self):
        try:
            uri = f"{self.ws_url}/ws/{self.symbol}"
            async with websockets.connect(uri) as websocket:
                self.websocket = websocket
                self.running = True
                self.connection_status.emit("Connected")

                while self.running:
                    try:
                        # Use wait_for with timeout to allow checking running status
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        if not self.running:
                            break
                        data = json.loads(message)
                        self.data_received.emit(data)
                    except asyncio.TimeoutError:
                        # Timeout is expected, just continue the loop
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        logger.info("WebSocket connection closed")
                        break

        except Exception as e:
            if self.running:  # Only log if we weren't intentionally stopping
                logger.exception("WebSocket connection error")
                self.connection_status.emit(f"Error: {e}")

    async def send_command(self, command):
        try:
            if self.websocket:
                await self.websocket.send(json.dumps(command))
        except Exception as e:
            logger.error(f"Error sending WebSocket command: {e}")

    def stop(self):
        self.running = False
        
        if self.websocket and not self.websocket.close:
            try:
                # Close the websocket connection
                if self.loop and self.loop.is_running():
                    self.loop.call_soon_threadsafe(
                        lambda: asyncio.create_task(self.websocket.close())
                    )
            except Exception as e:
                logger.warning(f"Failed to close websocket: {e}")
        
        # Stop the event loop gracefully
        if self.loop and self.loop.is_running():
            try:
                self.loop.call_soon_threadsafe(self.loop.stop)
            except Exception as e:
                logger.warning(f"Failed to stop event loop: {e}")
        
        # Wait for thread to finish with timeout
        if not self.wait(3000):  # 3 second timeout
            logger.warning("WebSocket thread did not stop gracefully")
            self.terminate()  # Force terminate if needed


class ChartWidget(QWidget):
    # Add signal to request data reload
    data_reload_requested = pyqtSignal(str, str)  # symbol, timeframe
    
    def __init__(self):
        super().__init__()
        self.ws_thread = None
        self.current_symbol = None
        self.current_timeframe = None
        self.original_data = None  # Store original data
        self.replay_data = []
        self.is_replaying = False
        self.is_paused = False
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.title_label = QLabel("Select a symbol to view chart")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
        layout.addWidget(self.title_label)

        self.setup_replay_controls(layout)

        self.chart = QtChart(self, toolbox=True)
        webview = self.chart.get_webview()
        self.setMinimumSize(600, 400)
        webview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(webview)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: gray; font-size: 11px; padding: 3px;")
        layout.addWidget(self.status_label)

    def setup_replay_controls(self, parent_layout):
        controls_widget = QWidget()
        controls_layout = QHBoxLayout(controls_widget)
        controls_layout.setContentsMargins(0, 0, 0, 0)

        replay_label = QLabel("Replay:")
        replay_label.setFont(QFont("Arial", 9, QFont.Bold))
        controls_layout.addWidget(replay_label)

        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setMaximumWidth(120)
        controls_layout.addWidget(self.start_date)

        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems(["1m", "5m", "15m", "1h", "4h", "1d"])
        self.timeframe_combo.setCurrentText("1h")
        self.timeframe_combo.setMaximumWidth(80)
        controls_layout.addWidget(self.timeframe_combo)

        controls_layout.addWidget(QLabel("Speed:"))

        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 100)
        self.speed_slider.setValue(10)
        self.speed_slider.setMaximumWidth(100)
        self.speed_slider.valueChanged.connect(self.update_speed_label)
        controls_layout.addWidget(self.speed_slider)

        self.speed_label = QLabel("1.0x")
        self.speed_label.setMinimumWidth(40)
        controls_layout.addWidget(self.speed_label)

        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(self.start_replay)
        self.start_btn.setMaximumWidth(60)
        controls_layout.addWidget(self.start_btn)

        self.pause_btn = QPushButton("Pause")
        self.pause_btn.clicked.connect(self.pause_replay)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setMaximumWidth(60)
        controls_layout.addWidget(self.pause_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_replay)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setMaximumWidth(60)
        controls_layout.addWidget(self.stop_btn)

        controls_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        parent_layout.addWidget(controls_widget)

    def update_speed_label(self):
        speed = self.speed_slider.value() / 10.0
        self.speed_label.setText(f"{speed:.1f}x")

    def set_data(self, data: MarketDataResponse):
        try:
            if self.is_replaying:
                return
            
            df = pd.DataFrame([{
                'time': pd.to_datetime(bar.time),
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close
            } for bar in data.data])
            
            if not df.empty:
                self.chart.set(df)
                self.title_label.setText(f"{data.symbol} - {data.timeframe}")
                self.current_symbol = data.symbol
                self.current_timeframe = data.timeframe
                # Store the original data for restoration after replay
                self.original_data = data
                
        except Exception as e:
            logger.exception("Error setting chart data")
            self.status_label.setText(f"Error setting data: {e}")

    def start_replay(self):
        if not self.current_symbol:
            self.status_label.setText("No symbol selected")
            return

        if self.ws_thread and self.ws_thread.isRunning():
            self.stop_replay()

        self.chart.set(None)
        self.replay_data = []

        self.ws_thread = WebSocketThread(self.current_symbol)
        self.ws_thread.data_received.connect(self.handle_replay_data)
        self.ws_thread.connection_status.connect(self.handle_connection_status)
        self.ws_thread.start()

        QTimer.singleShot(1000, self.send_start_command)

        self.is_replaying = True
        self.is_paused = False
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("Starting replay...")

    def send_start_command(self):
        if self.ws_thread and self.ws_thread.websocket:
            command = {
                "command": "start",
                "timeframe": self.timeframe_combo.currentText(),
                "speed": self.speed_slider.value() / 10.0,
                "start_date": self.start_date.date().toString("yyyy-MM-dd")
            }
            if self.ws_thread.loop and self.ws_thread.loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.ws_thread.send_command(command),
                    self.ws_thread.loop
                )

    def pause_replay(self):
        if not self.ws_thread:
            return
        command = {"command": "pause" if not self.is_paused else "resume"}
        self.pause_btn.setText("Resume" if not self.is_paused else "Pause")
        self.is_paused = not self.is_paused
        self.status_label.setText("Replay paused" if self.is_paused else "Replay resumed")
        QTimer.singleShot(100, lambda: self.send_ws_command(command))

    def stop_replay(self):
        if self.ws_thread:
            self.send_ws_command({"command": "stop"})
            self.ws_thread.stop()
            self.ws_thread = None

        self.is_replaying = False
        self.is_paused = False
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("Pause")
        self.stop_btn.setEnabled(False)
        self.status_label.setText("Replay stopped")
        
        # Restore original data or request fresh data
        self.restore_original_data()

    def restore_original_data(self):
        """Restore original data after replay stops"""
        try:
            if self.original_data:
                # Restore from cached original data
                self.set_data(self.original_data)
                self.status_label.setText("Original data restored")
            elif self.current_symbol and self.current_timeframe:
                # Request fresh data from parent/API
                self.data_reload_requested.emit(self.current_symbol, self.current_timeframe)
                self.status_label.setText("Reloading current symbol data...")
            else:
                self.status_label.setText("Ready")
        except Exception as e:
            logger.exception("Error restoring original data")
            self.status_label.setText(f"Error restoring data: {e}")
            # Try to request fresh data as fallback
            if self.current_symbol:
                self.data_reload_requested.emit(self.current_symbol, self.current_timeframe or "1h")

    def send_ws_command(self, command):
        try:
            if self.ws_thread and self.ws_thread.loop and self.ws_thread.loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.ws_thread.send_command(command),
                    self.ws_thread.loop
                )
        except Exception as e:
            logger.exception("Error sending WebSocket command")

    def handle_replay_data(self, data):
        try:
            msg_type = data.get('type')
            if msg_type == 'bar':
                bar = data['bar']
                self.replay_data.append({
                    'time': pd.to_datetime(bar['timestamp']),
                    'open': float(bar['open']),
                    'high': float(bar['high']),
                    'low': float(bar['low']),
                    'close': float(bar['close'])
                })
                if len(self.replay_data) == 1:
                    self.chart.set(pd.DataFrame(self.replay_data))
                else:
                    self.chart.update(pd.Series(self.replay_data[-1]))
                self.status_label.setText(f"Replay: {len(self.replay_data)} bars")

            elif msg_type == 'finished':
                self.status_label.setText("Replay completed")
                self.stop_replay()

            elif msg_type == 'error':
                self.status_label.setText(f"Error: {data.get('message', 'Unknown error')}")

        except Exception as e:
            logger.exception("Error handling replay data")
            self.status_label.setText(f"Data error: {e}")

    def handle_connection_status(self, status):
        self.status_label.setText(status)

    def closeEvent(self, event):
        if self.ws_thread:
            self.ws_thread.stop()
        event.accept()