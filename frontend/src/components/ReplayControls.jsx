import React, { useState, useEffect } from 'react';

const ReplayControls = ({
  symbol = 'COPPER',
  timeframe = '1h',
  onReplayData,
  onReplayStatusChange,
  onReplayStartDateChange,
  isWebSocketConnected = true,
  sendWebSocketCommand,
  onReconnect,
  currentBar = null,
  replayStatus = null
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [speed, setSpeed] = useState(1.0);
  const [startDate, setStartDate] = useState('');
  const [status, setStatus] = useState('Ready');

  const speedOptions = [
    { value: 0.25, label: '0.25x' },
    { value: 0.5, label: '0.5x' },
    { value: 1.0, label: '1x' },
    { value: 2.0, label: '2x' },
    { value: 5.0, label: '5x' },
    { value: 10.0, label: '10x' }
  ];
  useEffect(() => {
    if (replayStatus) {
      const isCurrentlyPlaying = ['playing', 'starting'].includes(replayStatus.status);
      const isCurrentlyPaused = replayStatus.status === 'paused';
      
      setIsPlaying(isCurrentlyPlaying || isCurrentlyPaused);
      setIsPaused(isCurrentlyPaused);
      
      const statusMap = {
        'playing': 'Playing',
        'paused': 'Paused',
        'stopped': 'Stopped',
        'finished': 'Finished',
        'error': 'Error',
        'starting': 'Starting...'
      };
      setStatus(statusMap[replayStatus.status] || 'Ready');
    } else {
      setIsPlaying(false);
      setIsPaused(false);
      setStatus('Ready');
    }
  }, [replayStatus]);

  useEffect(() => {
    if (isWebSocketConnected) {
      if (!replayStatus || replayStatus.status === 'stopped') {
        setStatus('Ready for Replay');
      }
    } else {
      setStatus('Disconnected');
      if (!replayStatus || !['playing', 'paused'].includes(replayStatus.status)) {
        setIsPlaying(false);
        setIsPaused(false);
      }
    }
  }, [isWebSocketConnected, replayStatus]);

  const formatDateTimeForBackend = (dateTimeLocal) => {
    if (!dateTimeLocal) return '';

    const date = new Date(dateTimeLocal);
    const offsetMinutes = date.getTimezoneOffset();
    const offsetHours = Math.floor(Math.abs(offsetMinutes) / 60);
    const offsetMins = Math.abs(offsetMinutes) % 60;
    const offsetSign = offsetMinutes <= 0 ? '+' : '-';
    const offsetString = `${offsetSign}${offsetHours.toString().padStart(2, '0')}:${offsetMins.toString().padStart(2, '0')}`;

    return date.toISOString().slice(0, -1) + offsetString;
  };

  const handlePlay = () => {
    if (!isWebSocketConnected) {
      console.log('Not connected, attempting to reconnect...');
      if (onReconnect) {
        onReconnect();
      }
      return;
    }

    const commandData = { speed };
    if (startDate) {
      const formattedDate = formatDateTimeForBackend(startDate);
      commandData.start_date = formattedDate;
      
      if (onReplayStartDateChange) {
        onReplayStartDateChange(formattedDate);
      }
    }

    if (sendWebSocketCommand) {
      sendWebSocketCommand('start', commandData);
    }
    setStatus('Starting replay...');
    setIsPlaying(true);
    setIsPaused(false);
  };

  const handlePause = () => {
    if (sendWebSocketCommand) {
      sendWebSocketCommand('pause');
    }
    setStatus('Pausing...');
    setIsPaused(true);
  };

  const handleResume = () => {
    if (sendWebSocketCommand) {
      sendWebSocketCommand('resume');
    }
    setStatus('Resuming...');
    setIsPaused(false);
  };

  const handleStop = () => {
    if (sendWebSocketCommand) {
      sendWebSocketCommand('stop');
    }
    setIsPlaying(false);
    setIsPaused(false);
    setStatus('Stopping...');
  };

  const handleSpeedChange = (newSpeed) => {
    setSpeed(newSpeed);
    console.log('Speed changed to:', newSpeed);

    if (isPlaying && !isPaused && isWebSocketConnected) {
      const commandData = { speed: newSpeed };
      if (startDate) {
        commandData.start_date = formatDateTimeForBackend(startDate);
      }
      if (sendWebSocketCommand) {
        sendWebSocketCommand('start', commandData);
      }
    }
  };

  const handleStartDateChange = (e) => {
    const newStartDate = e.target.value;
    setStartDate(newStartDate);
    
    if (newStartDate && onReplayStartDateChange) {
      const formattedDate = formatDateTimeForBackend(newStartDate);
      onReplayStartDateChange(formattedDate);
    }
  };

  return (
    <div style={styles.replayControls}>
      {/* Controls Section */}
      <div style={styles.controlsSection}>
        <div style={styles.controlsRow}>
          {/* Date Selection */}
          <div style={styles.controlGroup}>
            <label style={styles.label} htmlFor="start-date">Start Date & Time:</label>
            <input
              id="start-date"
              type="datetime-local"
              value={startDate}
              onChange={handleStartDateChange}
              disabled={isPlaying && !isPaused}
              style={{...styles.input, ...(isPlaying && !isPaused ? styles.inputDisabled : {})}}
            />
          </div>

          {/* Speed Selection */}
          <div style={styles.controlGroup}>
            <label style={styles.label} htmlFor="speed">Playback Speed:</label>
            <select
              id="speed"
              value={speed}
              onChange={(e) => handleSpeedChange(parseFloat(e.target.value))}
              style={styles.select}
            >
              {speedOptions.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Playback Controls */}
      <div style={styles.playbackControls}>
        {!isPlaying ? (
          <button
            style={{...styles.controlBtn, ...styles.playBtn}}
            onClick={handlePlay}
            disabled={!symbol || !isWebSocketConnected}
            title="Start replay"
          >
            <span style={styles.btnIcon}>▶️</span>
            <span>Play</span>
          </button>
        ) : (
          <div style={styles.activeControls}>
            {!isPaused ? (
              <button
                style={{...styles.controlBtn, ...styles.pauseBtn}}
                onClick={handlePause}
                title="Pause replay"
              >
                <span style={styles.btnIcon}>⏸️</span>
                <span>Pause</span>
              </button>
            ) : (
              <button
                style={{...styles.controlBtn, ...styles.resumeBtn}}
                onClick={handleResume}
                title="Resume replay"
              >
                <span style={styles.btnIcon}>▶️</span>
                <span>Resume</span>
              </button>
            )}
            <button
              style={{...styles.controlBtn, ...styles.stopBtn}}
              onClick={handleStop}
              title="Stop replay"
            >
              <span style={styles.btnIcon}>⏹️</span>
              <span>Stop</span>
            </button>
          </div>
        )}

        {/* Connection Controls */}
        {!isWebSocketConnected && (
          <button
            style={{...styles.controlBtn, ...styles.connectBtn}}
            onClick={onReconnect}
            title="Reconnect to server"
          >
            <span style={styles.btnIcon}>🔄</span>
            <span>Reconnect</span>
          </button>
        )}
      </div>

      {/* Current Bar Info */}
      {currentBar && (
        <div style={styles.currentBarInfo}>
          <h4 style={styles.barTitle}>Current Bar</h4>
          <div style={styles.barDetails}>
            <div style={styles.barTime}>
              {new Date(currentBar.timestamp).toLocaleString()}
            </div>
            <div style={styles.ohlcData}>
              <span style={styles.ohlcItem}>O: <strong>{currentBar?.open?.toFixed(4)}</strong></span>
              <span style={styles.ohlcItem}>H: <strong>{currentBar?.high?.toFixed(4)}</strong></span>
              <span style={styles.ohlcItem}>L: <strong>{currentBar?.low?.toFixed(4)}</strong></span>
              <span style={styles.ohlcItem}>C: <strong>{currentBar?.close?.toFixed(4)}</strong></span>
            </div>
          </div>
        </div>
      )}

      {/* Help Text */}
      {!isPlaying && isWebSocketConnected && (
        <div style={styles.helpText}>
          <small>
            💡 Select a start date and click Play to begin replay. 
            Leave date empty to start from the beginning of available data.
          </small>
        </div>
      )}

      {/* Debug Info */}
      <div style={styles.debugInfo}>
        <details>
          <summary style={styles.debugSummary}>Debug Info</summary>
          <div style={styles.debugDetails}>
            <div>WebSocket Connected: {isWebSocketConnected.toString()}</div>
            <div>Is Playing: {isPlaying.toString()}</div>
            <div>Is Paused: {isPaused.toString()}</div>
            <div>Current Speed: {speed}x</div>
            <div>Start Date: {startDate || 'Not set'}</div>
            <div>Replay Status: {replayStatus?.status || 'None'}</div>
          </div>
        </details>
      </div>
    </div>
  );
};

const styles = {
  replayControls: {
    background: 'linear-gradient(145deg, #1e2139, #1a1d35)',
    border: '1px solid #2d3147',
    borderRadius: '12px',
    padding: '16px',
    margin: '16px 0',
    color: '#e2e4ea',
    boxShadow: '0 4px 16px rgba(0, 0, 0, 0.3)',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    width: '100%',
    maxWidth: '100%',
    boxSizing: 'border-box'
  },
  
  controlsHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '20px',
    paddingBottom: '16px',
    borderBottom: '1px solid #2d3147'
  },
  
  title: {
    margin: 0,
    color: '#ffffff',
    fontSize: '18px',
    fontWeight: '600',
    background: 'linear-gradient(135deg, #4fc3f7, #29b6f6)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    backgroundClip: 'text'
  },
  
  connectionStatus: {
    padding: '6px 14px',
    borderRadius: '20px',
    fontSize: '12px',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    display: 'flex',
    alignItems: 'center',
    gap: '6px'
  },
  
  connected: {
    background: 'linear-gradient(135deg, #4caf50, #26a69a)',
    color: 'white',
    boxShadow: '0 2px 8px rgba(76, 175, 80, 0.3)'
  },
  
  disconnected: {
    background: 'linear-gradient(135deg, #f44336, #d32f2f)',
    color: 'white',
    boxShadow: '0 2px 8px rgba(244, 67, 54, 0.3)'
  },
  
  playing: {
    background: 'linear-gradient(135deg, #4caf50, #26a69a)',
    color: 'white',
    boxShadow: '0 2px 8px rgba(76, 175, 80, 0.3)'
  },
  
  paused: {
    background: 'linear-gradient(135deg, #ff9800, #f57c00)',
    color: 'white',
    boxShadow: '0 2px 8px rgba(255, 152, 0, 0.3)'
  },
  
  statusIndicator: {
    fontSize: '10px'
  },
  
  controlsSection: {
    marginBottom: '20px'
  },
  
  controlsRow: {
    display: 'flex',
    gap: '12px',
    marginBottom: '16px',
    alignItems: 'flex-end',
    flexWrap: 'wrap'
  },
  
  controlGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    flex: 1,
    minWidth: '140px',
    maxWidth: '100%'
  },
  
  label: {
    fontSize: '12px',
    color: '#9ca3af',
    fontWeight: '500',
    textTransform: 'uppercase',
    letterSpacing: '0.5px'
  },
  
  input: {
    padding: '10px 14px',
    border: '2px solid #2d3147',
    borderRadius: '8px',
    background: '#151829',
    color: '#e2e4ea',
    fontSize: '13px',
    transition: 'all 0.3s ease',
    outline: 'none',
    width: '100%',
    boxSizing: 'border-box'
  },
  
  inputDisabled: {
    opacity: '0.5',
    cursor: 'not-allowed'
  },
  
  select: {
    padding: '10px 14px',
    border: '2px solid #2d3147',
    borderRadius: '8px',
    background: '#151829',
    color: '#e2e4ea',
    fontSize: '13px',
    transition: 'all 0.3s ease',
    outline: 'none',
    cursor: 'pointer',
    width: '100%',
    boxSizing: 'border-box'
  },
  
  playbackControls: {
    display: 'flex',
    gap: '8px',
    alignItems: 'center',
    justifyContent: 'center',
    margin: '20px 0',
    flexWrap: 'wrap',
    width: '100%'
  },
  
  activeControls: {
    display: 'flex',
    gap: '8px',
    alignItems: 'center',
    flexWrap: 'wrap',
    width: '100%',
    justifyContent: 'center'
  },
  
  controlBtn: {
    padding: '10px 16px',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: '600',
    transition: 'all 0.3s ease',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    minWidth: '80px',
    maxWidth: '120px',
    justifyContent: 'center',
    outline: 'none',
    flex: '1 1 auto',
    whiteSpace: 'nowrap'
  },
  
  btnIcon: {
    fontSize: '16px'
  },
  
  playBtn: {
    background: 'linear-gradient(135deg, #4caf50, #26a69a)',
    color: 'white',
    boxShadow: '0 2px 8px rgba(76, 175, 80, 0.3)'
  },
  
  pauseBtn: {
    background: 'linear-gradient(135deg, #ff9800, #f57c00)',
    color: 'white',
    boxShadow: '0 2px 8px rgba(255, 152, 0, 0.3)'
  },
  
  resumeBtn: {
    background: 'linear-gradient(135deg, #4caf50, #26a69a)',
    color: 'white',
    boxShadow: '0 2px 8px rgba(76, 175, 80, 0.3)'
  },
  
  stopBtn: {
    background: 'linear-gradient(135deg, #f44336, #d32f2f)',
    color: 'white',
    boxShadow: '0 2px 8px rgba(244, 67, 54, 0.3)'
  },
  
  connectBtn: {
    background: 'linear-gradient(135deg, #2196f3, #1976d2)',
    color: 'white',
    boxShadow: '0 2px 8px rgba(33, 150, 243, 0.3)'
  },
  
  replayInfo: {
    background: 'linear-gradient(145deg, #151829, #1a1d35)',
    border: '1px solid #2d3147',
    borderRadius: '8px',
    padding: '16px',
    marginBottom: '16px'
  },
  
  infoRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '8px'
  },
  
  infoLabel: {
    fontSize: '12px',
    color: '#9ca3af',
    fontWeight: '500',
    textTransform: 'uppercase',
    letterSpacing: '0.5px'
  },
  
  infoValue: {
    fontSize: '14px',
    color: '#e2e4ea',
    fontWeight: '600'
  },
  
  speedIndicator: {
    color: '#4fc3f7'
  },
  
  currentBarInfo: {
    background: 'linear-gradient(145deg, #151829, #1a1d35)',
    border: '1px solid #2d3147',
    borderRadius: '8px',
    padding: '16px',
    marginBottom: '16px',
    position: 'relative'
  },
  
  barTitle: {
    margin: '0 0 12px 0',
    color: '#ffffff',
    fontSize: '14px',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: '0.5px'
  },
  
  barDetails: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    width: '100%'
  },
  
  barTime: {
    fontSize: '12px',
    color: '#9ca3af',
    textAlign: 'center',
    padding: '8px',
    background: '#1a1d35',
    borderRadius: '6px',
    border: '1px solid #2d3147'
  },
  
  ohlcData: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(50px, 1fr))',
    gap: '4px',
    width: '100%'
  },
  
  ohlcItem: {
    background: 'linear-gradient(145deg, #1a1d35, #151829)',
    padding: '4px 6px',
    borderRadius: '6px',
    border: '1px solid #2d3147',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '10px',
    fontWeight: '500',
    textAlign: 'center',
    minHeight: '32px',
    boxSizing: 'border-box',
    overflow: 'hidden',
    whiteSpace: 'nowrap'
  },
  
  volumeData: {
    background: 'linear-gradient(145deg, #1a1d35, #151829)',
    padding: '8px 12px',
    borderRadius: '6px',
    border: '1px solid #2d3147',
    fontSize: '12px',
    fontWeight: '500',
    textAlign: 'center'
  },
  
  helpText: {
    background: 'linear-gradient(145deg, #0f1219, #151829)',
    border: '1px solid #2d3147',
    borderRadius: '6px',
    padding: '12px',
    fontSize: '12px',
    color: '#9ca3af',
    textAlign: 'center',
    marginBottom: '16px'
  },
  
  debugInfo: {
    background: 'linear-gradient(145deg, #0a0d14, #0f1219)',
    border: '1px solid #1e2139',
    borderRadius: '6px',
    padding: '12px',
    fontFamily: '"Courier New", monospace',
    fontSize: '11px',
    color: '#6b7280'
  },
  
  debugSummary: {
    cursor: 'pointer',
    fontSize: '12px',
    fontWeight: '600',
    color: '#9ca3af',
    marginBottom: '8px'
  },
  
  debugDetails: {
    marginTop: '8px'
  }
};

export default ReplayControls;