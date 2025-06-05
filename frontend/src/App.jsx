// frontend/src/App.js
import React, { useState, useCallback, useRef, useEffect } from 'react';
import './App.css';
import TradingChart from './components/TradingChart';
import ReplayControls from './components/ReplayControls';
import SymbolSelector from './components/SymbolSelector';

function App() {
  const [selectedSymbol, setSelectedSymbol] = useState('');
  const [selectedTimeframe, setSelectedTimeframe] = useState('1h');
  const [isReplayMode, setIsReplayMode] = useState(false);
  const [replayData, setReplayData] = useState(null);
  const [replayStatus, setReplayStatus] = useState(null);
  const [replayStartDate, setReplayStartDate] = useState(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Add loading states
  const [isSymbolLoading, setIsSymbolLoading] = useState(false);
  const [availableSymbols, setAvailableSymbols] = useState([]);
  const [symbolLoadError, setSymbolLoadError] = useState(null);

  const [isWebSocketConnected, setIsWebSocketConnected] = useState(false);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  // Load available symbols on component mount
  useEffect(() => {
    const loadSymbols = async () => {
      setIsSymbolLoading(true);
      setSymbolLoadError(null);

      try {
        const response = await fetch('http://localhost:8000/symbols');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const symbols = await response.json();
        setAvailableSymbols(symbols);
      } catch (error) {
        console.error('Error loading symbols:', error);
        setSymbolLoadError(error.message);
        // Fallback to common symbols if API fails
        setAvailableSymbols(['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']);
      } finally {
        setIsSymbolLoading(false);
      }
    };

    loadSymbols();
  }, []);

  const handleSymbolChange = useCallback((symbol) => {
    // Only close WebSocket if we're not in replay mode or if replay is stopped
    if (wsRef.current && (!isReplayMode || (replayStatus && replayStatus.status === 'stopped'))) {
      wsRef.current.close();
    }

    setSelectedSymbol(symbol);

    // Only reset replay mode if not currently playing
    if (!isReplayMode || (replayStatus && ['stopped', 'finished', 'error'].includes(replayStatus.status))) {
      setIsReplayMode(false);
      setReplayData(null);
      setReplayStatus(null);
      setReplayStartDate(null);
    }
  }, [isReplayMode, replayStatus]);

  const handleTimeframeChange = useCallback((timeframe) => {
    setSelectedTimeframe(timeframe);

    // Only reset replay if not currently playing
    if (isReplayMode && replayStatus && ['stopped', 'finished', 'error'].includes(replayStatus.status)) {
      setIsReplayMode(false);
      setReplayData(null);
      setReplayStatus(null);
      setReplayStartDate(null);
    }
  }, [isReplayMode, replayStatus]);

  const handleReplayData = useCallback((barData) => {
    setReplayData(barData);
    if (!isReplayMode) {
      setIsReplayMode(true);
    }
  }, [isReplayMode]);

  const handleReplayStatusChange = useCallback((status) => {
    setReplayStatus(status);

    if (status.status === 'stopped' || status.status === 'finished') {
      // Don't automatically exit replay mode, just update status
      // Let user manually exit if they want
      setReplayData(null);
      setReplayStartDate(null);
    }
  }, []);

  const handleReplayStartDateChange = useCallback((startDate) => {
    console.log('Replay start date changed:', startDate);
    setReplayStartDate(startDate);
  }, []);

  const connectWebSocket = useCallback(() => {
    if (!selectedSymbol) return;

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      return;
    }

    if (wsRef.current) {
      wsRef.current.close();
    }

    try {
      const wsUrl = `ws://localhost:8000/ws/${selectedSymbol}`;
      console.log('Connecting to:', wsUrl);

      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        setIsWebSocketConnected(true);
        reconnectAttempts.current = 0;
        console.log('WebSocket connected for', selectedSymbol);
      };

      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('Received WebSocket message:', data);
          handleWebSocketMessage(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      wsRef.current.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        setIsWebSocketConnected(false);

        // Only attempt reconnection if in replay mode and not manually closed
        if (isReplayMode && event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.pow(2, reconnectAttempts.current) * 1000;
          console.log(`Attempting to reconnect in ${delay}ms (attempt ${reconnectAttempts.current + 1})`);

          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current++;
            if (selectedSymbol && isReplayMode) {
              connectWebSocket();
            }
          }, delay);
        }
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

    } catch (error) {
      console.error('Error creating WebSocket:', error);
    }
  }, [selectedSymbol, isReplayMode]);

  const handleWebSocketMessage = useCallback((data) => {
    switch (data.type) {
      case 'connected':
        break;

      case 'replay_started':
        if (data.start_date) {
          handleReplayStartDateChange(data.start_date);
        }
        break;

      case 'bar':
        handleReplayData(data.bar);
        handleReplayStatusChange({
          isPlaying: true,
          isPaused: false,
          status: 'playing',
          currentBar: data.bar
        });
        break;

      case 'paused':
        handleReplayStatusChange({
          isPlaying: false,
          isPaused: true,
          status: 'paused',
          currentBar: null
        });
        break;

      case 'resumed':
        handleReplayStatusChange({
          isPlaying: true,
          isPaused: false,
          status: 'playing',
          currentBar: null
        });
        break;

      case 'stopped':
        handleReplayStatusChange({
          isPlaying: false,
          isPaused: false,
          status: 'stopped',
          currentBar: null
        });
        break;

      case 'finished':
        handleReplayStatusChange({
          isPlaying: false,
          isPaused: false,
          status: 'finished',
          currentBar: null
        });
        break;

      case 'error':
        console.error('Replay error:', data.message);
        handleReplayStatusChange({
          isPlaying: false,
          isPaused: false,
          status: 'error',
          currentBar: null
        });
        break;

      default:
        console.log('Unknown message type:', data.type);
    }
  }, [handleReplayData, handleReplayStatusChange, handleReplayStartDateChange]);

  useEffect(() => {
    if (isReplayMode && selectedSymbol && !isWebSocketConnected) {
      connectWebSocket();
    }

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [isReplayMode, selectedSymbol, isWebSocketConnected, connectWebSocket]);

  const toggleReplayMode = useCallback(() => {
    if (isReplayMode) {
      // Send stop command before closing WebSocket if replay is active
      if (replayStatus && ['playing', 'paused'].includes(replayStatus.status)) {
        sendWebSocketCommand('stop');
      }

      // Give a moment for the stop command to be sent
      setTimeout(() => {
        if (wsRef.current) {
          wsRef.current.close(1000, 'User exited replay mode'); // Normal closure
        }
        setIsReplayMode(false);
        setReplayData(null);
        setReplayStatus(null);
        setReplayStartDate(null);
      }, 100);
    } else {
      setIsReplayMode(true);
    }
  }, [isReplayMode, replayStatus]);

  const formatStatusDisplay = (status) => {
    if (!status) return 'Unknown';

    const statusMap = {
      'connected': 'Connected',
      'playing': 'Playing',
      'paused': 'Paused',
      'stopped': 'Stopped',
      'finished': 'Completed',
      'error': 'Error'
    };

    return statusMap[status] || status;
  };

  const sendWebSocketCommand = useCallback((command, additionalData = {}) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const message = {
        command,
        symbol: selectedSymbol,
        timeframe: selectedTimeframe,
        ...additionalData
      };

      console.log('Sending command:', message);
      wsRef.current.send(JSON.stringify(message));
      return true;
    } else {
      console.error('WebSocket not connected');
      return false;
    }
  }, [selectedSymbol, selectedTimeframe]);

  // Retry symbol loading function
  const retrySymbolLoading = useCallback(() => {
    const loadSymbols = async () => {
      setIsSymbolLoading(true);
      setSymbolLoadError(null);

      try {
        const response = await fetch('http://localhost:8000/symbols');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const symbols = await response.json();
        setAvailableSymbols(symbols);
      } catch (error) {
        console.error('Error loading symbols:', error);
        setSymbolLoadError(error.message);
      } finally {
        setIsSymbolLoading(false);
      }
    };

    loadSymbols();
  }, []);

  return (
    <div className="App">
      {/* Header */}
      <header className="app-header-compact">
        <div className="header-left">
          <button
            className="sidebar-toggle"
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          >
            {sidebarCollapsed ? '→' : '←'}
          </button>
          <h1>Trading Replay Platform</h1>
          {selectedSymbol && (
            <div className="header-symbol-info">
              <span className="symbol-display">{selectedSymbol}</span>
              <span className="timeframe-display">{selectedTimeframe}</span>
            </div>
          )}
        </div>

        <div className="header-right">
          <span className={`mode-badge ${isReplayMode ? 'replay' : 'live'}`}>
            {isReplayMode ? '🔄 REPLAY' : '📊 CHART'}
          </span>
          {replayStatus && (
            <span className={`status-badge ${replayStatus.status}`}>
              {formatStatusDisplay(replayStatus.status)}
            </span>
          )}
          {isReplayMode && (
            <span className={`connection-badge ${isWebSocketConnected ? 'connected' : 'disconnected'}`}>
              {isWebSocketConnected ? '🟢' : '🔴'}
            </span>
          )}
        </div>
      </header>

      <div className="app-layout-maximized">
        {/* Sidebar */}
        <aside className={`sidebar-compact ${sidebarCollapsed ? 'collapsed' : ''}`}>
          {!sidebarCollapsed && (
            <>
              <div className="sidebar-section">
                <SymbolSelector
                  selectedSymbol={selectedSymbol}
                  onSymbolChange={handleSymbolChange}
                  disabled={isReplayMode && replayStatus && ['playing', 'paused'].includes(replayStatus.status)}
                  availableSymbols={availableSymbols}
                  isLoading={isSymbolLoading}
                  error={symbolLoadError}
                  onRetry={retrySymbolLoading}
                />
              </div>

              {selectedSymbol && (
                <div className="sidebar-section">
                  <button
                    className={`mode-toggle-btn ${isReplayMode ? 'exit' : 'enter'}`}
                    onClick={toggleReplayMode}
                  >
                    {isReplayMode ? '← Exit Replay' : '▶️ Start Replay'}
                  </button>
                </div>
              )}

              {isReplayMode && selectedSymbol && (
                <div className="sidebar-section">
                  <ReplayControls
                    symbol={selectedSymbol}
                    timeframe={selectedTimeframe}
                    onReplayData={handleReplayData}
                    onReplayStatusChange={handleReplayStatusChange}
                    onReplayStartDateChange={handleReplayStartDateChange}
                    isWebSocketConnected={isWebSocketConnected}
                    sendWebSocketCommand={sendWebSocketCommand}
                    onReconnect={connectWebSocket}
                    currentBar={replayStatus?.currentBar || null}
                    replayStatus={replayStatus}
                  />
                </div>
              )}

              {/* Replay Status */}
              {replayStatus && (
                <div className="sidebar-section">
                  <div className="replay-status-compact">
                    <h4>Status</h4>
                    <div className="status-grid">
                      <div className="status-row">
                        <span>State:</span>
                        <span className={`status-value ${replayStatus.status}`}>
                          {formatStatusDisplay(replayStatus.status)}
                        </span>
                      </div>
                      {replayStartDate && (
                        <div className="status-row">
                          <span>Start:</span>
                          <span className="status-value">
                            {new Date(replayStartDate).toLocaleString()}
                          </span>
                        </div>
                      )}
                      {replayStatus.currentBar && (
                        <>
                          <div className="status-row">
                            <span>Time:</span>
                            <span className="status-value">
                              {new Date(replayStatus.currentBar.timestamp).toLocaleTimeString()}
                            </span>
                          </div>
                          <div className="status-row">
                            <span>Price:</span>
                            <span className="status-value">
                              ${replayStatus.currentBar.close.toFixed(4)}
                            </span>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </aside>

        {/* Chart Area */}
        <main className="main-content-maximized">
          {selectedSymbol ? (
            <TradingChart
              symbol={selectedSymbol}
              timeframe={selectedTimeframe}
              onTimeframeChange={handleTimeframeChange}
              isReplayMode={isReplayMode}
              replayData={replayData}
              replayStartDate={replayStartDate}
            />
          ) : (
            <div className="no-symbol-selected-compact">
              <div className="placeholder-content-compact">
                <h2>Select a Symbol to Begin</h2>
                <p>Choose a trading symbol from the sidebar to view charts and start replay analysis</p>
                <div className="quick-features">
                  <span>📊 Real-time Charts</span>
                  <span>🔄 Historical Replay</span>
                  <span>⏯️ Playback Controls</span>
                  <span>📈 Multiple Timeframes</span>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Footer */}
      <footer className="app-footer-compact">
        <div className="footer-content-compact">
          <span>Trading Replay Platform</span>
          {selectedSymbol && (
            <>
              <span>•</span>
              <span>{selectedSymbol} - {selectedTimeframe}</span>
            </>
          )}
          <span>•</span>
          <span>Historical Market Data Analysis</span>
        </div>
      </footer>
    </div>
  );
}

export default App;