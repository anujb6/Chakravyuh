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
      <header className="app-header">
        <h1>Trading Replay Platform</h1>
        <div className="mode-indicator">
          <span className={`mode-badge ${isReplayMode ? 'replay' : 'live'}`}>
            {isReplayMode ? '🔄 REPLAY MODE' : '📊 CHART MODE'}
          </span>
        </div>
      </header>

      <div className="app-layout">
        {/* Left Sidebar */}
        <aside className="sidebar">
          <SymbolSelector
            selectedSymbol={selectedSymbol}
            onSymbolChange={handleSymbolChange}
            disabled={isReplayMode}
          />

          {selectedSymbol && (
            <div className="mode-controls">
              <button
                className={`mode-toggle-btn ${isReplayMode ? 'exit' : 'enter'}`}
                onClick={toggleReplayMode}
              >
                {isReplayMode ? '← Exit Replay' : '▶️ Start Replay'}
              </button>
            </div>
          )}

          {/* Replay Status */}
          {replayStatus && (
            <div className="replay-status">
              <h4>Replay Status</h4>
              <div className="status-info">
                <div className="status-item">
                  <span>State:</span>
                  <span className={`status-value ${replayStatus.status}`}>
                    {formatStatusDisplay(replayStatus.status)}
                  </span>
                </div>
                <div className="status-item">
                  <span>Playing:</span>
                  <span className={`status-value ${replayStatus.isPlaying ? 'yes' : 'no'}`}>
                    {replayStatus.isPlaying ? 'Yes' : 'No'}
                  </span>
                </div>
                <div className="status-item">
                  <span>Paused:</span>
                  <span className={`status-value ${replayStatus.isPaused ? 'yes' : 'no'}`}>
                    {replayStatus.isPaused ? 'Yes' : 'No'}
                  </span>
                </div>
                {replayStatus.currentBar && (
                  <>
                    <div className="status-item">
                      <span>Current Time:</span>
                      <span className="status-value">
                        {new Date(replayStatus.currentBar.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <div className="status-item">
                      <span>Current Price:</span>
                      <span className="status-value">
                        ${replayStatus.currentBar.close.toFixed(4)}
                      </span>
                    </div>
                  </>
                )}
              </div>
            </div>
          )}

          {/* Replay Controls */}
          {isReplayMode && selectedSymbol && (
            <ReplayControls
              symbol={selectedSymbol}
              timeframe={selectedTimeframe}
              onReplayData={handleReplayData}
              onReplayStatusChange={handleReplayStatusChange}
            />
          )}
        </aside>

        {/* Main Content */}
        <main className="main-content">
          {selectedSymbol ? (
            <TradingChart
              symbol={selectedSymbol}
              timeframe={selectedTimeframe}
              onTimeframeChange={handleTimeframeChange}
              isReplayMode={isReplayMode}
              replayData={replayData}
            />
          ) : (
            <div className="no-symbol-selected">
              <div className="placeholder-content">
                <h2>Welcome to Trading Replay Platform</h2>
                <p>Select a symbol from the sidebar to start viewing charts</p>
                <div className="features-list">
                  <h3>Features:</h3>
                  <ul>
                    <li>📊 Real-time chart viewing</li>
                    <li>🔄 Historical data replay</li>
                    <li>⏯️ Playback controls with speed adjustment</li>
                    <li>📈 Multiple timeframes support</li>
                    <li>📊 Volume analysis</li>
                  </ul>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Footer */}
      <footer className="app-footer">
        <div className="footer-content">
          <span>Trading Replay Platform</span>
          <span>•</span>
          <span>Historical Market Data Analysis</span>
          {selectedSymbol && (
            <>
              <span>•</span>
              <span>{selectedSymbol} - {selectedTimeframe}</span>
            </>
          )}
        </div>
      </footer>
    </div>
  );
}

export default App;