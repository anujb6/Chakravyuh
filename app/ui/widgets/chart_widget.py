import logging
import pandas as pd
import numpy as np
import asyncio
import websockets
import json
from datetime import datetime, timedelta
import threading
import time

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QDateEdit, QSizePolicy, QSpacerItem, QCheckBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QDate
from PyQt5.QtGui import QFont, QIcon
from lightweight_charts.widgets import QtChart
from services.api_client import MarketDataResponse

logger = logging.getLogger(__name__)


class WebSocketThread(QThread):
    data_received = pyqtSignal(dict)
    connection_status = pyqtSignal(str)

    def __init__(self, symbol, ws_url="ws://localhost:8000"):
        super().__init__()
        self.symbol = symbol
        self.ws_url = ws_url
        self.websocket = None
        self.running = False
        self.loop = None
        self._stop_event = threading.Event()
        self._command_queue = None
        self._connection_ready = threading.Event()
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 3

    def run(self):
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.main_loop())
        except Exception as e:
            logger.exception("WebSocket thread error")
            self.connection_status.emit(f"Error: {e}")
        finally:
            self._cleanup_loop()

    def _cleanup_loop(self):
        if self.loop and not self.loop.is_closed():
            try:
                pending = asyncio.all_tasks(self.loop)
                if pending:
                    for task in pending:
                        task.cancel()
                    self.loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
            except Exception as e:
                logger.warning(f"Error during cleanup: {e}")
            finally:
                self.loop.close()

    async def main_loop(self):
        self.running = True
        self._command_queue = asyncio.Queue()
        
        while self.running and self._reconnect_attempts < self._max_reconnect_attempts:
            try:
                await self.connect_and_listen()
                if self.running:
                    self._reconnect_attempts += 1
                    if self._reconnect_attempts < self._max_reconnect_attempts:
                        logger.info(f"Attempting reconnection {self._reconnect_attempts}/{self._max_reconnect_attempts}")
                        self.connection_status.emit("Reconnecting...")
                        await asyncio.sleep(2)
                    else:
                        logger.error("Max reconnection attempts reached")
                        self.connection_status.emit("Connection failed")
                        break
            except Exception as e:
                logger.exception("Error in main loop")
                self.connection_status.emit(f"Connection error: {e}")
                self._reconnect_attempts += 1
                if self.running and self._reconnect_attempts < self._max_reconnect_attempts:
                    await asyncio.sleep(2)

    async def connect_and_listen(self):
        uri = f"{self.ws_url}/ws/{self.symbol}"
        
        try:
            async with websockets.connect(
                uri, 
                ping_interval=30,
                ping_timeout=10,
                close_timeout=10
            ) as websocket:
                self.websocket = websocket
                self._connection_ready.set()
                self.connection_status.emit("Connected")
                self._reconnect_attempts = 0
                logger.info(f"Connected to WebSocket: {uri}")

                listen_task = asyncio.create_task(self.listen_for_messages())
                command_task = asyncio.create_task(self.process_commands())

                try:
                    done, pending = await asyncio.wait(
                        [listen_task, command_task],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    for task in pending:
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
                            
                except Exception as e:
                    logger.exception("Error in task execution")
                    
        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"WebSocket connection closed: {e}")
            self.connection_status.emit("Disconnected")
        except Exception as e:
            logger.exception("WebSocket connection error")
            self.connection_status.emit(f"Error: {e}")
            raise
        finally:
            self.websocket = None
            self._connection_ready.clear()

    async def listen_for_messages(self):
        message_count = 0
        last_heartbeat = time.time()
        
        try:
            while self.running and self.websocket:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=5.0)
                    
                    if not self.running:
                        break
                        
                    data = json.loads(message)
                    message_count += 1
                    last_heartbeat = time.time()
                    
                    self.data_received.emit(data)
                    
                except asyncio.TimeoutError:
                    if time.time() - last_heartbeat > 60:
                        logger.warning("No messages received for 60 seconds, connection may be stale")
                        break
                    continue
                    
                except websockets.exceptions.ConnectionClosed:
                    logger.info("WebSocket connection closed during listen")
                    break
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON received: {e}")
                    continue
                    
        except Exception as e:
            logger.exception("Error in listen_for_messages")
            
        logger.info(f"Listen loop ended. Processed {message_count} messages")

    async def process_commands(self):
        commands_sent = 0
        
        try:
            while self.running:
                try:
                    command = await asyncio.wait_for(self._command_queue.get(), timeout=1.0)
                    
                    if self.websocket:
                        await self.websocket.send(json.dumps(command))
                        commands_sent += 1
                        logger.debug(f"Sent command #{commands_sent}: {command}")
                    else:
                        logger.warning("Cannot send command: WebSocket not connected")
                        
                    self._command_queue.task_done()
                        
                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed:
                    logger.info("WebSocket closed while sending command")
                    break
                except Exception as e:
                    logger.error(f"Error processing command: {e}")
                    
        except Exception as e:
            logger.exception("Error in process_commands")
            
        logger.info(f"Command processor ended. Sent {commands_sent} commands")

    def send_command(self, command):
        try:
            if not self.loop or self.loop.is_closed():
                logger.warning("Cannot send command: Event loop not available")
                return False
                
            if not self.running:
                logger.warning("Cannot send command: Thread not running")
                return False
                
            if not self._connection_ready.wait(timeout=10):
                logger.warning("Cannot send command: Connection not ready")
                return False
                
            future = asyncio.run_coroutine_threadsafe(
                self._command_queue.put(command), 
                self.loop
            )
            
            try:
                future.result(timeout=5)
                logger.debug(f"Queued command: {command}")
                return True
            except Exception as e:
                logger.error(f"Failed to queue command: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            return False

    def stop(self):
        logger.info("Stopping WebSocket thread...")
        self.running = False
        self._stop_event.set()
        
        self._connection_ready.clear()
        
        if not self.wait(8000):
            logger.warning("WebSocket thread did not stop gracefully, terminating...")
            self.terminate()
            self.wait(2000)
        else:
            logger.info("WebSocket thread stopped gracefully")


class ChartWidget(QWidget):
    data_reload_requested = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.ws_thread = None
        self.current_symbol = None
        self.current_timeframe = None
        self.original_data = None
        self.filtered_data = None
        self.replay_data = []
        self.is_replaying = False
        self.is_paused = False
        self.replay_start_time = None
        self._chart_prepared = False
        self.replay_timer = QTimer()
        self.replay_timer.timeout.connect(self._replay_next_candle)
        self.replay_index = 0
        self.replay_speed = 1000
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
        controls_layout.setContentsMargins(5, 0, 5, 0)
        controls_layout.setSpacing(10)

        replay_label = QLabel("Replay:")
        replay_label.setFont(QFont("Arial", 9, QFont.Bold))
        controls_layout.addWidget(replay_label)

        self.show_historical_checkbox = QCheckBox("Show Historical")
        self.show_historical_checkbox.setChecked(True)
        self.show_historical_checkbox.setToolTip("Show historical candles before replay start date")
        controls_layout.addWidget(self.show_historical_checkbox)

        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setCalendarPopup(True)
        self.start_date.setMaximumWidth(130)
        self.start_date.setToolTip("Start date for replay")
        self.start_date.setStyleSheet("""
            QDateEdit {
                padding: 2px 4px;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
        """)
        controls_layout.addWidget(self.start_date)

        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.5x", "1x", "2x", "5x", "10x"])
        self.speed_combo.setCurrentText("1x")
        self.speed_combo.setMaximumWidth(70)
        self.speed_combo.setToolTip("Replay speed")
        controls_layout.addWidget(self.speed_combo)

        button_style = """
            QPushButton {
                background-color: #2c7be5;
                color: white;
                padding: 4px 10px;
                border-radius: 5px;
            }
            QPushButton:disabled {
                background-color: #aaa;
                color: #eee;
            }
        """

        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(self.start_replay)
        self.start_btn.setMaximumWidth(70)
        self.start_btn.setStyleSheet(button_style)
        controls_layout.addWidget(self.start_btn)

        self.pause_btn = QPushButton("Pause")
        self.pause_btn.clicked.connect(self.pause_replay)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setMaximumWidth(70)
        self.pause_btn.setStyleSheet(button_style)
        controls_layout.addWidget(self.pause_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_replay)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setMaximumWidth(70)
        self.stop_btn.setStyleSheet(button_style)
        controls_layout.addWidget(self.stop_btn)

        controls_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        parent_layout.addWidget(controls_widget)

    def set_data(self, data: MarketDataResponse):
        try:
            if self.is_replaying:
                return

            times = pd.to_datetime([bar.time for bar in data.data])
            opens = np.array([bar.open for bar in data.data])
            highs = np.array([bar.high for bar in data.data])
            lows  = np.array([bar.low for bar in data.data])
            closes= np.array([bar.close for bar in data.data])

            df = pd.DataFrame({
                'time': pd.to_datetime(times),
                'open': opens,
                'high': highs,
                'low': lows,
                'close': closes
            })

            if not df.empty:
                self.chart.set(df)
                self.title_label.setText(f"{data.symbol} - {data.timeframe}")
                self.current_symbol = data.symbol
                self.current_timeframe = data.timeframe
                self.original_data = df.copy()

        except Exception as e:
            logger.exception("Error setting chart data")
            self.status_label.setText(f"Error setting data: {e}")

    def _filter_data_for_replay(self):
        try:
            if self.original_data is None or self.original_data.empty:
                self.status_label.setText("No data available for replay")
                return False

            replay_start = pd.to_datetime(self.start_date.date().toString("yyyy-MM-dd"), utc=True)
            
            if self.show_historical_checkbox.isChecked():
                historical_cutoff = replay_start - timedelta(days=30)
                self.filtered_data = self.original_data[
                    self.original_data['time'] >= historical_cutoff
                ].copy()
                
                historical_data = self.filtered_data[
                    self.filtered_data['time'] < replay_start
                ].copy()
                
                if not historical_data.empty:
                    self.chart.set(historical_data)
                else:
                    self.chart.set(None)
            else:
                self.filtered_data = self.original_data.copy()
                self.chart.set(None)

            self.replay_data = self.filtered_data[
                self.filtered_data['time'] >= replay_start
            ].copy().reset_index(drop=True)

            if self.replay_data.empty:
                self.status_label.setText("No data available for selected replay date")
                return False

            logger.info(f"Filtered data for replay: {len(self.replay_data)} bars from {replay_start}")
            return True

        except Exception as e:
            logger.exception("Error filtering data for replay")
            self.status_label.setText(f"Error filtering data: {e}")
            return False

    def start_replay(self):
        if not self.current_symbol or self.original_data is None:
            self.status_label.setText("No data available for replay")
            return

        self._clean_stop_replay()
        self._reset_replay_state()

        if not self._filter_data_for_replay():
            self._reset_ui_state()
            return

        speed_text = self.speed_combo.currentText()
        speed_multiplier = float(speed_text.replace('x', ''))
        self.replay_speed = int(1000 / speed_multiplier)

        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.is_replaying = True
        self.replay_index = 0

        self.status_label.setText(f"Starting replay from {self.start_date.date().toString('yyyy-MM-dd')}")
        self.replay_timer.start(self.replay_speed)

    def _clean_stop_replay(self):
        if self.replay_timer.isActive():
            self.replay_timer.stop()

    def _reset_replay_state(self):
        self.is_replaying = False
        self.is_paused = False
        self._chart_prepared = False
        self.replay_index = 0

    def _replay_next_candle(self):
        try:
            if not self.is_replaying or self.is_paused or self.replay_data is None:
                return

            if self.replay_index >= len(self.replay_data):
                self.status_label.setText("Replay completed")
                QTimer.singleShot(1000, self.stop_replay)
                return

            row = self.replay_data.iloc[self.replay_index]
            bar_series = pd.Series({
                'time': row['time'],
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close']
            })

            self.chart.update(bar_series)
            self.replay_index += 1

            progress = f"{self.replay_index}/{len(self.replay_data)}"
            if self.show_historical_checkbox.isChecked() and self.filtered_data is not None:
                historical_count = len(self.filtered_data) - len(self.replay_data)
                total_displayed = historical_count + self.replay_index
                self.status_label.setText(f"Replay: {progress} ({total_displayed} total bars)")
            else:
                self.status_label.setText(f"Replay: {progress}")

        except Exception as e:
            logger.exception("Error replaying candle")
            self.status_label.setText(f"Replay error: {e}")
            self.stop_replay()

    def pause_replay(self):
        if not self.is_replaying:
            return

        if self.is_paused:
            self.replay_timer.start(self.replay_speed)
            self.pause_btn.setText("Pause")
            self.is_paused = False
            self.status_label.setText("Replay resumed")
        else:
            self.replay_timer.stop()
            self.pause_btn.setText("Resume")
            self.is_paused = True
            self.status_label.setText("Replay paused")

    def stop_replay(self):
        try:
            self._clean_stop_replay()
            self._reset_ui_state()
            self.status_label.setText("Replay stopped")
            
            QTimer.singleShot(500, self.restore_original_data)
            
        except Exception as e:
            logger.exception("Error stopping replay")
            self.status_label.setText(f"Error stopping replay: {e}")

    def _reset_ui_state(self):
        self.is_replaying = False
        self.is_paused = False
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("Pause")
        self.stop_btn.setEnabled(False)

    def restore_original_data(self):
        try:
            if self.original_data is not None and not self.original_data.empty:
                self.chart.set(self.original_data)
                self.status_label.setText("Original data restored")
            elif self.current_symbol and self.current_timeframe:
                self.data_reload_requested.emit(self.current_symbol, self.current_timeframe)
                self.status_label.setText("Reloading current symbol data...")
            else:
                self.status_label.setText("Ready")
        except Exception as e:
            logger.exception("Error restoring original data")
            self.status_label.setText(f"Error restoring data: {e}")

    def closeEvent(self, event):
        try:
            self._clean_stop_replay()
        except:
            pass
        event.accept()