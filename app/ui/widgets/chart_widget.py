import logging
import pandas as pd
import numpy as np
import asyncio
import websockets
import json
from datetime import datetime, timedelta
import threading
import time
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, List

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QDateEdit, QSizePolicy, QSpacerItem, QCheckBox, QDoubleSpinBox,
    QGroupBox, QGridLayout
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QDate
from PyQt5.QtGui import QFont, QIcon
from lightweight_charts.widgets import QtChart
from services.api_client import MarketDataResponse

logger = logging.getLogger(__name__)


class PositionSide(Enum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class Position:
    symbol: str
    side: PositionSide
    size: float
    entry_price: float
    stop_loss: Optional[float] = None
    current_price: Optional[float] = None
    unrealized_pnl: float = 0.0
    entry_time: Optional[datetime] = None
    
    def update_pnl(self, current_price: float):
        self.current_price = current_price
        if self.side == PositionSide.LONG:
            self.unrealized_pnl = (current_price - self.entry_price) * self.size
        else:
            self.unrealized_pnl = (self.entry_price - current_price) * self.size


class PositionManager:
    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.position_updated = None  # Signal will be set by parent
        
    def open_position(self, symbol: str, side: PositionSide, size: float, entry_price: float, stop_loss: Optional[float] = None):
        position = Position(
            symbol=symbol,
            side=side,
            size=size,
            entry_price=entry_price,
            stop_loss=stop_loss,
            entry_time=datetime.now()
        )
        self.positions[symbol] = position
        if self.position_updated:
            self.position_updated.emit(position)
        return position
    
    def close_position(self, symbol: str):
        if symbol in self.positions:
            position = self.positions.pop(symbol)
            if self.position_updated:
                self.position_updated.emit(None)  # Signal position closed
            return position
        return None
    
    def update_stop_loss(self, symbol: str, new_stop_loss: float):
        if symbol in self.positions:
            self.positions[symbol].stop_loss = new_stop_loss
            if self.position_updated:
                self.position_updated.emit(self.positions[symbol])
    
    def update_current_prices(self, symbol: str, price: float):
        if symbol in self.positions:
            self.positions[symbol].update_pnl(price)
            if self.position_updated:
                self.position_updated.emit(self.positions[symbol])
    
    def get_position(self, symbol: str) -> Optional[Position]:
        return self.positions.get(symbol)
    
    def has_position(self, symbol: str) -> bool:
        return symbol in self.positions


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
    position_updated = pyqtSignal(object)

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
        self.global_pnl = 0.0
        self.session_pnl = 0.0
        self._stop_loss_hit = False
        
        # Position management
        self.position_manager = PositionManager()
        self.position_manager.position_updated = self.position_updated
        self.current_position_line = None  # Entry price line
        self.current_stop_loss_line = None  # Stop loss line
        self.latest_price = None
        self.position_updated.connect(self.on_position_updated)
        
        self.setup_ui()
        
        # Connect chart events for stop loss dragging
        self.setup_chart_events()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.title_label = QLabel("Select a symbol to view chart")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
        layout.addWidget(self.title_label)

        # Controls row
        controls_row = QHBoxLayout()
        self.setup_replay_controls(controls_row)
        self.setup_position_controls(controls_row)
        
        controls_widget = QWidget()
        controls_widget.setLayout(controls_row)
        layout.addWidget(controls_widget)

        self.chart = QtChart(self, toolbox=True)
        webview = self.chart.get_webview()
        self.setMinimumSize(800, 500)
        webview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(webview)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: gray; font-size: 11px; padding: 3px;")
        layout.addWidget(self.status_label)

    def setup_replay_controls(self, parent_layout):
        group = QGroupBox("Replay")
        layout = QHBoxLayout(group)

        self.show_historical_checkbox = QCheckBox("Historical")
        self.show_historical_checkbox.setChecked(True)
        layout.addWidget(self.show_historical_checkbox)

        self.start_date = QDateEdit(QDate.currentDate().addDays(-30))
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setCalendarPopup(True)
        self.start_date.setMaximumWidth(130) 

        self.start_date.setStyleSheet("""
            QDateEdit {
                padding: 2px 6px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 12px;
                color: white;
            }
            QDateEdit:hover {
                border: 1px solid #999;
                color: white;
            }
            QDateEdit::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid #ccc;
            }
        """)

        layout.addWidget(self.start_date)

        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.5x", "1x", "2x", "5x", "10x"])
        self.speed_combo.setCurrentText("1x")
        self.speed_combo.setMaximumWidth(80)  # Compact width
        self.speed_combo.currentTextChanged.connect(self.update_replay_speed)

        self.speed_combo.setStyleSheet("""
            QComboBox {
                padding: 2px 6px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 12px;
            }
            QComboBox:hover {
                border: 1px solid #999;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid #ccc;
            }
            QComboBox::down-arrow {
                image: url(:/qt-project.org/styles/commonstyle/images/arrowdown-16.png);
                width: 5px;
                height: 5px;
                margin: auto;
            }
        """)

        layout.addWidget(self.speed_combo)

        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(self.start_replay)
        layout.addWidget(self.start_btn)

        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self.pause_replay)
        layout.addWidget(self.pause_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_replay)
        layout.addWidget(self.stop_btn)

        parent_layout.addWidget(group)


    def setup_position_controls(self, parent_layout):
        group = QGroupBox("Position")
        layout = QHBoxLayout(group)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)

        self.position_size_spin = QDoubleSpinBox()
        self.position_size_spin.setRange(0.01, 1_000_000)
        self.position_size_spin.setValue(1.0)
        self.position_size_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.position_size_spin.setFixedWidth(75)
        self.position_size_spin.setFixedHeight(25)
        label_size = QLabel("Size:")
        label_size.setStyleSheet("padding: 0 3px; border: none")
        layout.addWidget(label_size)
        layout.addWidget(self.position_size_spin)

        self.stop_loss_price_spin = QDoubleSpinBox()
        self.stop_loss_price_spin.setRange(0.01, 1_000_000)
        self.stop_loss_price_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stop_loss_price_spin.setFixedWidth(75)
        self.stop_loss_price_spin.setFixedHeight(25)
        label_size = QLabel("SL:")
        label_size.setStyleSheet("padding: 0 2px; border: none")
        layout.addWidget(label_size)
        layout.addWidget(self.stop_loss_price_spin)

        self.long_btn = QPushButton("LONG")
        self.long_btn.setMaximumWidth(100)
        self.long_btn.clicked.connect(lambda: self.open_position(PositionSide.LONG))
        layout.addWidget(self.long_btn)

        self.short_btn = QPushButton("SHORT")
        self.short_btn.setMaximumWidth(100)
        self.short_btn.clicked.connect(lambda: self.open_position(PositionSide.SHORT))
        layout.addWidget(self.short_btn)

        self.close_btn = QPushButton("CLOSE")
        self.close_btn.setMaximumWidth(60)
        self.close_btn.setEnabled(False)
        self.close_btn.clicked.connect(self.close_position)
        layout.addWidget(self.close_btn)

        layout.addSpacing(10)
        label_global = QLabel("Global P&L:")
        label_global.setStyleSheet("padding: 0 6px;")
        layout.addWidget(label_global)
        self.global_pnl_label = QLabel("$0.00")
        self.global_pnl_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.global_pnl_label.setMinimumWidth(60)
        self.global_pnl_label.setStyleSheet("padding: 0 6px;")
        layout.addWidget(self.global_pnl_label)

        label_session = QLabel("Session P&L:")
        label_session.setStyleSheet("padding: 0 6px;")
        layout.addWidget(label_session)
        self.session_pnl_label = QLabel("$0.00")
        self.session_pnl_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.session_pnl_label.setMinimumWidth(60)
        self.session_pnl_label.setStyleSheet("padding: 0 6px;")
        layout.addWidget(self.session_pnl_label)

        layout.addStretch()
        parent_layout.addWidget(group)


    def setup_chart_events(self):
        """Setup chart event handlers for interactive stop loss"""
        try:
            # This would be called when chart is ready
            QTimer.singleShot(1000, self._delayed_chart_setup)
        except Exception as e:
            logger.error(f"Error setting up chart events: {e}")

    def _delayed_chart_setup(self):
        """Delayed setup of chart events after chart is ready"""
        try:
            if hasattr(self.chart, 'events'):
                # Set up click event for manual stop loss adjustment
                self.chart.events.click += self.on_chart_click
        except Exception as e:
            logger.debug(f"Chart events not available yet: {e}")

    def on_chart_click(self, chart, time, price):
        """Handle chart clicks for stop loss adjustment"""
        try:
            position = self.position_manager.get_position(self.current_symbol)
            if position and self.current_stop_loss_line:
                # Allow click-to-move stop loss
                if abs(price - position.stop_loss) < abs(price - position.entry_price):
                    self.update_stop_loss_price(price)
        except Exception as e:
            logger.error(f"Error handling chart click: {e}")

    def open_position(self, side: PositionSide):
        try:
            if not self.current_symbol or not self.latest_price:
                self.status_label.setText("No current price available")
                return

            if self.position_manager.has_position(self.current_symbol):
                self.status_label.setText("Position already exists for this symbol")
                return

            size = self.position_size_spin.value()
            entry_price = self.latest_price
            stop_loss = self.stop_loss_price_spin.value() 
            self.session_pnl_label.setText("$0")
            self.session_pnl_label.setStyleSheet("font-weight: bold; font-size: 10px;")

            if (side == PositionSide.LONG and stop_loss >= entry_price) or \
            (side == PositionSide.SHORT and stop_loss <= entry_price):
                self.status_label.setText("Invalid stop loss for selected position side")
                return

            position = self.position_manager.open_position(
                self.current_symbol, side, size, entry_price, stop_loss
            )

            self._draw_position_lines(position)
            self._update_position_ui(True)
            self.status_label.setText(f"Opened {side.value} position at {entry_price:.2f}, SL: {stop_loss:.2f}")

        except Exception as e:
            logger.error(f"Error opening position: {e}")
            self.status_label.setText(f"Error opening position: {e}")

    def close_position(self):
        try:
            if not self.current_symbol:
                return

            position = self.position_manager.close_position(self.current_symbol)
            if position:
                # ADDED: Update global and session P&L
                pnl = position.unrealized_pnl
                self.global_pnl += pnl
                self.session_pnl += pnl
                
                # Update P&L displays
                self._update_global_pnl_display()
                self._update_session_pnl_display()
                
                self._remove_position_lines()
                self._update_position_ui(False)
                self._stop_loss_hit = False
                self.status_label.setText(f"Closed position. P&L: ${pnl:.2f}")
            else:
                self.status_label.setText("No position to close")

        except Exception as e:
            logger.error(f"Error closing position: {e}")
            self.status_label.setText(f"Error closing position: {e}")

    def update_stop_loss_price(self, new_price: float):
        try:
            if self.current_symbol and self.current_stop_loss_line:
                self.position_manager.update_stop_loss(self.current_symbol, new_price)
                if self.current_stop_loss_line:
                    # Add null check before update
                    self.current_stop_loss_line.update(new_price)
                    self.current_stop_loss_line.label(f"SL: {new_price:.2f}")
                self.status_label.setText(f"Stop loss updated to {new_price:.2f}")
        except Exception as e:
            logger.error(f"Error updating stop loss: {e}")
    
    def _update_global_pnl_display(self):
        color = "green" if self.global_pnl >= 0 else "red"
        self.global_pnl_label.setText(f"${self.global_pnl:.2f}")
        self.global_pnl_label.setStyleSheet(
            f"font-weight: bold; font-size: 10px; color: {color};"
        )
        
    def _update_session_pnl_display(self):
        color = "green" if self.session_pnl >= 0 else "red"
        self.session_pnl_label.setText(f"${self.session_pnl:.2f}")
        self.session_pnl_label.setStyleSheet(
            f"font-weight: bold; font-size: 10px; color: {color};"
        )


    def _draw_position_lines(self, position: Position):
        try:
            self.current_position_line = self.chart.horizontal_line(
                position.entry_price,
                color='rgba(0, 123, 255, 0.8)',
                width=2,
                text=f"Entry: {position.entry_price:.2f}",
                axis_label_visible=True
            )

            self.current_stop_loss_line = self.chart.horizontal_line(
                position.stop_loss,
                color='rgba(220, 53, 69, 0.8)',
                width=2,
                text=f"SL: {position.stop_loss:.2f}",
                axis_label_visible=True,
                func=self._on_stop_loss_moved  # 💡 this enables dragging
            )

        except Exception as e:
            logger.error(f"Error drawing position lines: {e}")

            
    def _on_stop_loss_moved(self, chart, line):
        try:
            if self.current_symbol:
                new_price = line.price
                self.position_manager.update_stop_loss(self.current_symbol, new_price)
                self.status_label.setText(f"Stop loss moved to {new_price:.2f}")
        except Exception as e:
            logger.error(f"Error in stop loss move callback: {e}")


    def _remove_position_lines(self):
        try:
            if self.current_position_line:
                try:
                    self.current_position_line.delete()
                except Exception as e:
                    logger.warning(f"Failed to delete entry line: {e}")
                finally:
                    # Ensure reference is cleared
                    self.current_position_line = None

            if self.current_stop_loss_line:
                try:
                    self.current_stop_loss_line.delete()
                except Exception as e:
                    logger.warning(f"Failed to delete stop loss line: {e}")
                finally:
                    # Ensure reference is cleared
                    self.current_stop_loss_line = None
        except Exception as e:
            logger.error(f"Error in remove position line: {e}")

    def _update_position_ui(self, has_position: bool):
        """Update position-related UI elements"""
        self.long_btn.setEnabled(not has_position)
        self.short_btn.setEnabled(not has_position)
        self.close_btn.setEnabled(has_position)
        
        if not has_position:
            self.session_pnl_label.setText("$0.00")

    def _update_pnl_display(self, position: Position):
        """Update P&L display"""
        if position:
            pnl = position.unrealized_pnl
            color = "green" if pnl >= 0 else "red"
            self.session_pnl_label.setText(f"${pnl:.2f}")
            self.session_pnl_label.setStyleSheet(
                f"font-weight: bold; font-size: 10px; color: {color};"
            )

    def update_replay_speed(self):
        """Update replay speed while replay is running"""
        if not self.is_replaying or self.is_paused:
            return
        
        try:
            speed_text = self.speed_combo.currentText()
            speed_multiplier = float(speed_text.replace('x', ''))
            new_speed = int(1000 / speed_multiplier)
            
            if new_speed != self.replay_speed:
                self.replay_speed = new_speed
                
                if self.replay_timer.isActive():
                    self.replay_timer.stop()
                    self.replay_timer.start(self.replay_speed)
                
                self.status_label.setText(f"Speed changed to {speed_text}")
                
        except Exception as e:
            logger.error(f"Error updating replay speed: {e}")

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
                
                self.latest_price = closes[-1]
                if self.position_manager.has_position(data.symbol):
                    self.position_manager.update_current_prices(data.symbol, self.latest_price)

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

        self.update_replay_speed_value()

        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.is_replaying = True
        self.replay_index = 0
        
        self.session_pnl = 0.0
        self.session_pnl_label.setText("$0.00")
        self.session_pnl_label.setStyleSheet("font-weight: bold; font-size: 10px;")

        self.status_label.setText(f"Starting replay from {self.start_date.date().toString('yyyy-MM-dd')}")
        self.replay_timer.start(self.replay_speed)
        
    def update_replay_speed_value(self):
        speed_text = self.speed_combo.currentText()
        speed_multiplier = float(speed_text.replace('x', ''))
        self.replay_speed = int(1000 / speed_multiplier)

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
            
            self.latest_price = row['close']
            if self.position_manager.has_position(self.current_symbol):
                self.position_manager.update_current_prices(self.current_symbol, self.latest_price)
                position = self.position_manager.get_position(self.current_symbol)
                if position and position.stop_loss and not self._stop_loss_hit:
                    if ((position.side == PositionSide.LONG and self.latest_price <= position.stop_loss) or
                        (position.side == PositionSide.SHORT and self.latest_price >= position.stop_loss)):
                        self._stop_loss_hit = True
                        self.close_position()
                        self.status_label.setText(f"Stop loss hit at {self.latest_price:.2f}")

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
            self.update_replay_speed_value()
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

            # Reset P&L values
            self.global_pnl = 0.0
            self.session_pnl = 0.0
            self.global_pnl_label.setText("$0.00")
            self.session_pnl_label.setText("$0.00")

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
            if self.ws_thread and self.ws_thread.isRunning():
                self.ws_thread.stop()
        except:
            pass
        event.accept()

    def connect_websocket(self):
        if not self.current_symbol:
            self.status_label.setText("No symbol selected for WebSocket connection")
            return

        if self.ws_thread and self.ws_thread.isRunning():
            self.ws_thread.stop()

        self.ws_thread = WebSocketThread(self.current_symbol)
        self.ws_thread.data_received.connect(self.handle_websocket_data)
        self.ws_thread.connection_status.connect(self.handle_connection_status)
        self.ws_thread.start()

    def handle_websocket_data(self, data):
        try:
            if self.is_replaying:
                return

            if 'price' in data:
                price = float(data['price'])
                self.latest_price = price

                if self.position_manager.has_position(self.current_symbol):
                    self.position_manager.update_current_prices(self.current_symbol, price)
                    position = self.position_manager.get_position(self.current_symbol)
                    print(position)
                    if position:
                        self._update_pnl_display(position) 

            if 'candlestick' in data:
                candle = data['candlestick']
                bar_series = pd.Series({
                    'time': pd.to_datetime(candle['time']),
                    'open': float(candle['open']),
                    'high': float(candle['high']),
                    'low': float(candle['low']),
                    'close': float(candle['close'])
                })
                self.chart.update(bar_series)

        except Exception as e:
            logger.error(f"Error handling WebSocket data: {e}")

    def handle_connection_status(self, status):
        self.status_label.setText(f"WebSocket: {status}")

    def on_position_updated(self, position):
        if position:
            self._update_pnl_display(position)
        else:
            self._update_position_ui(False)
