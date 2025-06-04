// frontend/src/components/ReplayControls.js

import React, { useState, useEffect, useRef } from 'react';
import './ReplayControls.css';

const ReplayControls = ({
  symbol,
  timeframe,
  onReplayData,
  onReplayStatusChange,
  onReplayStartDateChange, // New prop from App.js
  isWebSocketConnected,
  sendWebSocketCommand,
  onReconnect
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [speed, setSpeed] = useState(1.0);
  const [startDate, setStartDate] = useState('');
  const [currentBar, setCurrentBar] = useState(null);
  const [status, setStatus] = useState('Ready');

  const speedOptions = [
    { value: 0.25, label: '0.25x' },
    { value: 0.5, label: '0.5x' },
    { value: 1.0, label: '1x' },
    { value: 2.0, label: '2x' },
    { value: 5.0, label: '5x' },
    { value: 10.0, label: '10x' }
  ];

  // Update local state based on WebSocket connection status
  useEffect(() => {
    if (isWebSocketConnected) {
      setStatus('Ready for Replay');
    } else {
      setStatus('Disconnected');
      setIsPlaying(false);
      setIsPaused(false);
    }
  }, [isWebSocketConnected]);

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
      
      // Notify parent about replay start date
      if (onReplayStartDateChange) {
        onReplayStartDateChange(formattedDate);
      }
    }

    if (sendWebSocketCommand('start', commandData)) {
      setStatus('Starting replay...');
      setIsPlaying(true);
      setIsPaused(false);
    }
  };

  const handlePause = () => {
    if (sendWebSocketCommand('pause')) {
      setStatus('Pausing...');
      setIsPaused(true);
    }
  };

  const handleResume = () => {
    if (sendWebSocketCommand('resume')) {
      setStatus('Resuming...');
      setIsPaused(false);
    }
  };

  const handleStop = () => {
    if (sendWebSocketCommand('stop')) {
      setIsPlaying(false);
      setIsPaused(false);
      setCurrentBar(null);
      setStatus('Stopping...');
    }
  };

  const handleSpeedChange = (newSpeed) => {
    setSpeed(newSpeed);
    console.log('Speed changed to:', newSpeed);

    // If currently playing, restart with new speed
    if (isPlaying && !isPaused && isWebSocketConnected) {
      const commandData = { speed: newSpeed };
      if (startDate) {
        commandData.start_date = formatDateTimeForBackend(startDate);
      }
      sendWebSocketCommand('start', commandData);
    }
  };

  const handleStartDateChange = (e) => {
    const newStartDate = e.target.value;
    setStartDate(newStartDate);
    
    // If we have a start date, notify parent immediately
    if (newStartDate && onReplayStartDateChange) {
      const formattedDate = formatDateTimeForBackend(newStartDate);
      onReplayStartDateChange(formattedDate);
    }
  };

  const getConnectionStatusClass = () => {
    if (!isWebSocketConnected) return 'disconnected';
    if (isPlaying && !isPaused) return 'playing';
    if (isPaused) return 'paused';
    return 'connected';
  };

  const getStatusDisplay = () => {
    if (!isWebSocketConnected) return 'Disconnected';
    if (isPlaying && isPaused) return 'Paused';
    if (isPlaying) return 'Playing';
    return 'Ready';
  };

  return (
    <div className="replay-controls">
      <div className="controls-header">
        <h3>Replay Controls</h3>
        <div className={`connection-status ${getConnectionStatusClass()}`}>
          <span className="status-indicator">
            {isWebSocketConnected ? '🟢' : '🔴'}
          </span>
          {getStatusDisplay()}
        </div>
      </div>

      <div className="controls-section">
        {/* Date Selection */}
        <div className="control-group">
          <label htmlFor="start-date">Start Date & Time:</label>
          <input
            id="start-date"
            type="datetime-local"
            value={startDate}
            onChange={handleStartDateChange}
            disabled={isPlaying && !isPaused}
            className="datetime-input"
          />
        </div>

        {/* Speed Selection */}
        <div className="control-group">
          <label htmlFor="speed">Playback Speed:</label>
          <select
            id="speed"
            value={speed}
            onChange={(e) => handleSpeedChange(parseFloat(e.target.value))}
            className="speed-select"
          >
            {speedOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Playback Controls */}
      <div className="playback-controls">
        {!isPlaying ? (
          <button
            className="control-btn play-btn primary"
            onClick={handlePlay}
            disabled={!symbol || !isWebSocketConnected}
            title="Start replay"
          >
            ▶️ Play
          </button>
        ) : (
          <div className="active-controls">
            {!isPaused ? (
              <button
                className="control-btn pause-btn"
                onClick={handlePause}
                title="Pause replay"
              >
                ⏸️ Pause
              </button>
            ) : (
              <button
                className="control-btn resume-btn primary"
                onClick={handleResume}
                title="Resume replay"
              >
                ▶️ Resume
              </button>
            )}
            <button
              className="control-btn stop-btn"
              onClick={handleStop}
              title="Stop replay"
            >
              ⏹️ Stop
            </button>
          </div>
        )}

        {/* Connection Controls */}
        {!isWebSocketConnected && (
          <button
            className="control-btn connect-btn"
            onClick={onReconnect}
            title="Reconnect to server"
          >
            🔄 Reconnect
          </button>
        )}
      </div>

      {/* Symbol and Timeframe Display */}
      <div className="replay-info">
        <div className="info-row">
          <span className="info-label">Symbol:</span>
          <span className="info-value">{symbol || 'None'}</span>
        </div>
        <div className="info-row">
          <span className="info-label">Timeframe:</span>
          <span className="info-value">{timeframe}</span>
        </div>
        {speed !== 1.0 && (
          <div className="info-row">
            <span className="info-label">Speed:</span>
            <span className="info-value speed-indicator">{speed}x</span>
          </div>
        )}
      </div>

      {/* Current Bar Info */}
      {currentBar && (
        <div className="current-bar-info">
          <h4>Current Bar</h4>
          <div className="bar-details">
            <div className="bar-time">
              {new Date(currentBar.timestamp).toLocaleString()}
            </div>
            <div className="ohlc-data">
              <span>O: <strong>{currentBar.open.toFixed(4)}</strong></span>
              <span>H: <strong>{currentBar.high.toFixed(4)}</strong></span>
              <span>L: <strong>{currentBar.low.toFixed(4)}</strong></span>
              <span>C: <strong>{currentBar.close.toFixed(4)}</strong></span>
            </div>
            <div className="volume-data">
              Volume: <strong>{currentBar.volume.toLocaleString()}</strong>
            </div>
          </div>
        </div>
      )}

      {/* Help Text */}
      {!isPlaying && isWebSocketConnected && (
        <div className="help-text">
          <small>
            💡 Select a start date and click Play to begin replay. 
            Leave date empty to start from the beginning of available data.
          </small>
        </div>
      )}

      {/* Debug Info (only in development) */}
      {process.env.NODE_ENV === 'development' && (
        <div className="debug-info">
          <details>
            <summary>Debug Info</summary>
            <div className="debug-details">
              <div>WebSocket Connected: {isWebSocketConnected.toString()}</div>
              <div>Is Playing: {isPlaying.toString()}</div>
              <div>Is Paused: {isPaused.toString()}</div>
              <div>Current Speed: {speed}x</div>
              <div>Start Date: {startDate || 'Not set'}</div>
            </div>
          </details>
        </div>
      )}
    </div>
  );
};

export default ReplayControls;