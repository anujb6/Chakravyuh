import logging
import pandas as pd
import numpy as np
import asyncio
import websockets
import json
import threading
import time
from PyQt5.QtCore import pyqtSignal

logger = logging.getLogger(__name__)
class WebSocketThread(threading.Thread):
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