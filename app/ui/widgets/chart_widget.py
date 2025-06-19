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
        """Clean up the event loop properly"""
        if self.loop and not self.loop.is_closed():
            try:
                # Cancel all tasks
                pending = asyncio.all_tasks(self.loop)
                if pending:
                    for task in pending:
                        task.cancel()
                    # Wait for cancellation
                    self.loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
            except Exception as e:
                logger.warning(f"Error during cleanup: {e}")
            finally:
                self.loop.close()

    async def main_loop(self):
        """Main async loop with better error handling and reconnection"""
        self.running = True
        self._command_queue = asyncio.Queue()
        
        while self.running and self._reconnect_attempts < self._max_reconnect_attempts:
            try:
                await self.connect_and_listen()
                # If we get here, connection was successful but closed
                if self.running:
                    self._reconnect_attempts += 1
                    if self._reconnect_attempts < self._max_reconnect_attempts:
                        logger.info(f"Attempting reconnection {self._reconnect_attempts}/{self._max_reconnect_attempts}")
                        self.connection_status.emit("Reconnecting...")
                        await asyncio.sleep(2)  # Wait before reconnecting
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
        """Connect to WebSocket with improved connection handling"""
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
                self._reconnect_attempts = 0  # Reset on successful connection
                logger.info(f"Connected to WebSocket: {uri}")

                # Create tasks
                listen_task = asyncio.create_task(self.listen_for_messages())
                command_task = asyncio.create_task(self.process_commands())

                # Wait for completion
                try:
                    done, pending = await asyncio.wait(
                        [listen_task, command_task],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    # Cancel pending tasks
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
        """Listen for messages with better error handling"""
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
                    
                    # Emit data in main thread
                    self.data_received.emit(data)
                    
                except asyncio.TimeoutError:
                    # Check for connection health
                    if time.time() - last_heartbeat > 60:  # No messages for 60 seconds
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
        """Process commands with better error handling"""
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
                        
                    # Mark task as done
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
        """Thread-safe command sending with better error handling"""
        try:
            if not self.loop or self.loop.is_closed():
                logger.warning("Cannot send command: Event loop not available")
                return False
                
            if not self.running:
                logger.warning("Cannot send command: Thread not running")
                return False
                
            # Wait for connection to be ready (with timeout)
            if not self._connection_ready.wait(timeout=10):
                logger.warning("Cannot send command: Connection not ready")
                return False
                
            future = asyncio.run_coroutine_threadsafe(
                self._command_queue.put(command), 
                self.loop
            )
            
            # Wait for command to be queued (with timeout)
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
        """Stop the WebSocket thread gracefully"""
        logger.info("Stopping WebSocket thread...")
        self.running = False
        self._stop_event.set()
        
        # Clear connection ready flag
        self._connection_ready.clear()
        
        # Give thread time to stop gracefully
        if not self.wait(8000):  # Increased timeout
            logger.warning("WebSocket thread did not stop gracefully, terminating...")
            self.terminate()
            self.wait(2000)
        else:
            logger.info("WebSocket thread stopped gracefully")


class ChartWidget(QWidget):
    data_reload_requested = pyqtSignal(str, str)
    historical_data_requested = pyqtSignal(str, str, str, str)

    def __init__(self):
        super().__init__()
        self.ws_thread = None
        self.current_symbol = None
        self.current_timeframe = None
        self.original_data = None
        self.historical_data = None
        self.replay_data = []
        self.is_replaying = False
        self.is_paused = False
        self.replay_start_time = None
        self._chart_prepared = False
        self._historical_loaded = False
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

            times = [bar.time for bar in data.data]
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
                self.original_data = data

        except Exception as e:
            logger.exception("Error setting chart data")
            self.status_label.setText(f"Error setting data: {e}")


    def set_historical_data(self, data: MarketDataResponse):
        """Set historical data for replay background"""
        try:
            if not data or not data.data:
                logger.warning("No historical data provided")
                self._historical_loaded = False
                return

            bars = data.data

            # Pre-allocate NumPy arrays
            n = len(bars)
            times = np.array([bar.time for bar in bars], dtype='datetime64[ns]')
            opens = np.empty(n, dtype=np.float64)
            highs = np.empty(n, dtype=np.float64)
            lows  = np.empty(n, dtype=np.float64)
            closes= np.empty(n, dtype=np.float64)

            for i, bar in enumerate(bars):
                opens[i] = bar.open
                highs[i] = bar.high
                lows[i]  = bar.low
                closes[i]= bar.close

            # Construct DataFrame directly from NumPy arrays
            df = pd.DataFrame({
                'time': times,
                'open': opens,
                'high': highs,
                'low': lows,
                'close': closes
            })

            # Sort by time
            self.historical_data = df.sort_values('time', kind='mergesort').reset_index(drop=True)
            self._historical_loaded = True

            logger.info(f"Historical data loaded: {len(self.historical_data)} bars")

        except Exception as e:
            logger.exception("Error setting historical data")
            self.status_label.setText(f"Error setting historical data: {e}")
            self._historical_loaded = False

    def start_replay(self):
        if not self.current_symbol:
            self.status_label.setText("No symbol selected")
            return

        self._clean_stop_replay()
        
        self._reset_replay_state()
        
        self._start_replay_process()

    def _clean_stop_replay(self):
        """Clean stop of any existing replay"""
        if self.ws_thread and self.ws_thread.isRunning():
            try:
                self.ws_thread.send_command({"command": "stop"})
            except:
                pass
            self.ws_thread.stop()
            self.ws_thread = None

    def _reset_replay_state(self):
        """Reset all replay-related state"""
        self.replay_data = []
        self.is_replaying = False
        self.is_paused = False
        self._chart_prepared = False
        self._historical_loaded = False
        self.historical_data = None
        self.replay_start_time = pd.to_datetime(self.start_date.date().toString("yyyy-MM-dd"))

    def _start_replay_process(self):
        """Start the complete replay process"""
        try:
            # Update UI state
            self.start_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
            
            if self.show_historical_checkbox.isChecked():
                self.status_label.setText("Loading historical data...")
                self._load_historical_data_for_replay()
            else:
                self._historical_loaded = True
                QTimer.singleShot(100, self._start_websocket_connection)
                
        except Exception as e:
            logger.exception("Error starting replay process")
            self.status_label.setText(f"Error starting replay: {e}")
            self._reset_ui_state()

    def _load_historical_data_for_replay(self):
        """Load historical data before starting replay"""
        try:
            historical_start = self.replay_start_time - timedelta(days=30)
            historical_end = self.replay_start_time - timedelta(days=1)
            
            self.historical_data_requested.emit(
                self.current_symbol,
                self.current_timeframe or "1h",
                historical_start.strftime("%Y-%m-%d"),
                historical_end.strftime("%Y-%m-%d")
            )
            
            # Give more time for historical data to load
            QTimer.singleShot(3000, self._check_and_start_connection)
            
        except Exception as e:
            logger.exception("Error loading historical data for replay")
            self.status_label.setText(f"Error loading historical data: {e}")
            self._reset_ui_state()

    def _check_and_start_connection(self):
        """Check if historical data is loaded and start connection"""
        if self.show_historical_checkbox.isChecked() and not self._historical_loaded:
            # Historical data still loading, wait a bit more
            QTimer.singleShot(1000, self._check_and_start_connection)
            return
            
        self._start_websocket_connection()

    def _start_websocket_connection(self):
        """Start the WebSocket connection for replay"""
        try:
            self.ws_thread = WebSocketThread(self.current_symbol)
            self.ws_thread.data_received.connect(self.handle_replay_data)
            self.ws_thread.connection_status.connect(self.handle_connection_status)
            self.ws_thread.start()

            self.is_replaying = True
            self.status_label.setText("Connecting to replay server...")
            
            # Wait for connection before sending start command
            QTimer.singleShot(2000, self._send_start_command_when_ready)
            
        except Exception as e:
            logger.exception("Error starting WebSocket connection")
            self.status_label.setText(f"Error connecting: {e}")
            self._reset_ui_state()

    def _send_start_command_when_ready(self):
        """Send start command when connection is ready"""
        try:
            if not self.ws_thread or not self.ws_thread.running:
                self.status_label.setText("Connection failed")
                self._reset_ui_state()
                return
                
            # Prepare chart first
            self._prepare_chart_for_replay()
            
            # Send start command
            command = {
                "command": "start",
                "timeframe": self.current_timeframe or "1h",
                "speed": 1.0,
                "start_date": self.start_date.date().toString("yyyy-MM-dd")
            }
            
            if self.ws_thread.send_command(command):
                self.status_label.setText("Replay started")
                logger.info(f"Sent start command: {command}")
            else:
                self.status_label.setText("Failed to start replay")
                self._reset_ui_state()
                
        except Exception as e:
            logger.exception("Error sending start command")
            self.status_label.setText(f"Error starting replay: {e}")
            self._reset_ui_state()

    def _prepare_chart_for_replay(self):
        """Prepare the chart with historical data if needed"""
        try:
            if self.show_historical_checkbox.isChecked() and self.historical_data is not None and not self.historical_data.empty:
                self.chart.set(self.historical_data)
                self._chart_prepared = True
                logger.info(f"Chart prepared with {len(self.historical_data)} historical bars")
            else:
                self.chart.set(None)
                self._chart_prepared = True
                
        except Exception as e:
            logger.exception("Error preparing chart for replay")
            self.status_label.setText(f"Error preparing chart: {e}")

    def pause_replay(self):
        if not self.ws_thread or not self.is_replaying:
            return
            
        try:
            command = {"command": "pause" if not self.is_paused else "resume"}
            
            if self.ws_thread.send_command(command):
                self.pause_btn.setText("Resume" if not self.is_paused else "Pause")
                self.is_paused = not self.is_paused
                self.status_label.setText("Replay paused" if self.is_paused else "Replay resumed")
            else:
                self.status_label.setText("Failed to pause/resume replay")
            
        except Exception as e:
            logger.exception("Error pausing/resuming replay")
            self.status_label.setText(f"Pause/Resume error: {e}")

    def stop_replay(self):
        try:
            self._clean_stop_replay()
            self._reset_ui_state()
            self.status_label.setText("Replay stopped")
            
            # Restore original data
            QTimer.singleShot(500, self.restore_original_data)
            
        except Exception as e:
            logger.exception("Error stopping replay")
            self.status_label.setText(f"Error stopping replay: {e}")

    def _reset_ui_state(self):
        """Reset UI state to non-replaying"""
        self.is_replaying = False
        self.is_paused = False
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("Pause")
        self.stop_btn.setEnabled(False)

    def restore_original_data(self):
        try:
            if self.original_data:
                self.set_data(self.original_data)
                self.status_label.setText("Original data restored")
            elif self.current_symbol and self.current_timeframe:
                self.data_reload_requested.emit(self.current_symbol, self.current_timeframe)
                self.status_label.setText("Reloading current symbol data...")
            else:
                self.status_label.setText("Ready")
        except Exception as e:
            logger.exception("Error restoring original data")
            self.status_label.setText(f"Error restoring data: {e}")

    def handle_replay_data(self, data):
        try:
            if not self.is_replaying:
                return
                
            msg_type = data.get('type')
            
            if msg_type == 'bar':
                self._handle_replay_bar(data['bar'])
            elif msg_type == 'finished':
                self.status_label.setText("Replay completed")
                QTimer.singleShot(1000, self.stop_replay)
            elif msg_type == 'error':
                error_msg = data.get('message', 'Unknown error')
                self.status_label.setText(f"Replay error: {error_msg}")
                logger.error(f"Replay error: {error_msg}")
                QTimer.singleShot(2000, self.stop_replay)
                
        except Exception as e:
            logger.exception("Error handling replay data")
            self.status_label.setText(f"Data handling error: {e}")

    def _handle_replay_bar(self, bar_data):
        """Handle individual replay bar data"""
        try:
            new_bar = {
                'time': pd.to_datetime(bar_data['timestamp']),
                'open': float(bar_data['open']),
                'high': float(bar_data['high']),
                'low': float(bar_data['low']),
                'close': float(bar_data['close'])
            }
            
            self.replay_data.append(new_bar)
            
            if len(self.replay_data) == 1:
                # First bar - handle initial chart setup
                if not self.show_historical_checkbox.isChecked() or self.historical_data is None or self.historical_data.empty:
                    # No historical data, start fresh
                    self.chart.set(pd.DataFrame([new_bar]))
                else:
                    # Add first replay bar to existing historical data
                    self.chart.update(pd.Series(new_bar))
            else:
                # Subsequent bars - just update
                self.chart.update(pd.Series(new_bar))
            
            # Update status
            replay_count = len(self.replay_data)
            if self.show_historical_checkbox.isChecked() and self.historical_data is not None:
                total_bars = len(self.historical_data) + replay_count
                self.status_label.setText(f"Replay: {replay_count} new bars ({total_bars} total)")
            else:
                self.status_label.setText(f"Replay: {replay_count} bars")
                
        except Exception as e:
            logger.exception("Error handling replay bar")
            self.status_label.setText(f"Bar processing error: {e}")

    def handle_connection_status(self, status):
        try:
            if "Connected" in status:
                self.status_label.setText("Connected - preparing replay...")
            elif "Error" in status or "Disconnected" in status:
                self.status_label.setText(status)
                if self.is_replaying:
                    QTimer.singleShot(3000, self.stop_replay)
            elif "Reconnecting" in status:
                self.status_label.setText("Reconnecting...")
                
        except Exception as e:
            logger.exception("Error handling connection status")

    def closeEvent(self, event):
        try:
            self._clean_stop_replay()
        except:
            pass
        event.accept()