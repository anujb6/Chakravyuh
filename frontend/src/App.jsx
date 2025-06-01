// frontend/src/App.js
import React, { useState, useCallback } from 'react';
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
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const handleSymbolChange = useCallback((symbol) => {
    setSelectedSymbol(symbol);
    setIsReplayMode(false);
    setReplayData(null);
  }, []);

  const handleTimeframeChange = useCallback((timeframe) => {
    setSelectedTimeframe(timeframe);
    if (isReplayMode) {
      setIsReplayMode(false);
      setReplayData(null);
    }
  }, [isReplayMode]);

  const handleReplayData = useCallback((barData) => {
    setReplayData(barData);
    if (!isReplayMode) {
      setIsReplayMode(true);
    }
  }, [isReplayMode]);

  const handleReplayStatusChange = useCallback((status) => {
    setReplayStatus(status);
    
    if (status.status === 'stopped' || status.status === 'finished') {
      setIsReplayMode(false);
      setReplayData(null);
    }
  }, []);

  const toggleReplayMode = () => {
    if (isReplayMode) {
      // Exit replay mode
      setIsReplayMode(false);
      setReplayData(null);
    } else {
      setIsReplayMode(true);
    }
  };

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

  return (
    <div className="App">
      {/* Compact Header */}
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
        </div>
      </header>

      <div className="app-layout-maximized">
        {/* Collapsible Sidebar */}
        <aside className={`sidebar-compact ${sidebarCollapsed ? 'collapsed' : ''}`}>
          {!sidebarCollapsed && (
            <>
              <div className="sidebar-section">
                <SymbolSelector
                  selectedSymbol={selectedSymbol}
                  onSymbolChange={handleSymbolChange}
                  disabled={isReplayMode}
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
                  />
                </div>
              )}

              {/* Compact Replay Status */}
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

        {/* Maximized Chart Area */}
        <main className="main-content-maximized">
          {selectedSymbol ? (
            <TradingChart
              symbol={selectedSymbol}
              timeframe={selectedTimeframe}
              onTimeframeChange={handleTimeframeChange}
              isReplayMode={isReplayMode}
              replayData={replayData}
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

      {/* Minimal Footer */}
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