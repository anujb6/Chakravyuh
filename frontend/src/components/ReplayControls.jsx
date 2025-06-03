// frontend/src/components/ReplayControls.js

import React, { useState, useEffect, useRef } from 'react';
import './ReplayControls.css';

const ReplayControls = ({
  symbol,
  timeframe,
  onReplayData,
  onReplayStatusChange
}) => {
  const [isConnected, setIsConnected] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [speed, setSpeed] = useState(1.0);
  const [startDate, setStartDate] = useState('');
  const [currentBar, setCurrentBar] = useState(null);
  const [status, setStatus] = useState('Disconnected');

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const speedOptions = [
    { value: 0.25, label: '0.25x' },
    { value: 0.5, label: '0.5x' },
    { value: 1.0, label: '1x' },
    { value: 2.0, label: '2x' },
    { value: 5.0, label: '5x' },
    { value: 10.0, label: '10x' }
  ];

  useEffect(() => {
    if (symbol) {
      connectWebSocket();
    }

    return () => {
      disconnectWebSocket();
    };
  }, [symbol]);

  const connectWebSocket = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      return; // Already connected
    }

    if (wsRef.current) {
      wsRef.current.close();
    }

    try {
      const wsUrl = `ws://localhost:8000/ws/${symbol}`;
      console.log('Connecting to:', wsUrl);

      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        setIsConnected(true);
        setStatus('Connected');
        reconnectAttempts.current = 0;
        console.log('WebSocket connected for', symbol);
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
        setIsConnected(false);
        setIsPlaying(false);
        setIsPaused(false);
        setStatus('Disconnected');

        // Attempt to reconnect with exponential backoff
        if (reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.pow(2, reconnectAttempts.current) * 1000; // 1s, 2s, 4s, 8s, 16s
          console.log(`Attempting to reconnect in ${delay}ms (attempt ${reconnectAttempts.current + 1})`);

          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current++;
            if (symbol) {
              connectWebSocket();
            }
          }, delay);
        } else {
          setStatus('Connection Failed - Max retries exceeded');
        }
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setStatus('Connection Error');
      };

    } catch (error) {
      console.error('Error creating WebSocket:', error);
      setStatus('Connection Failed');
    }
  };

  const disconnectWebSocket = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Component unmounting');
      wsRef.current = null;
    }
  };

  const handleWebSocketMessage = (data) => {
    console.log('Processing message:', data.type);

    switch (data.type) {
      case 'connected':
        setStatus('Ready for Replay');
        break;

      case 'bar':
        setCurrentBar(data.bar);
        setIsPlaying(true);
        setIsPaused(false);

        if (onReplayData) {
          console.log('Calling onReplayData with:', data.bar);
          onReplayData(data.bar);
        }

        const timestamp = new Date(data.bar.timestamp).toLocaleString();
        setStatus(`Playing - ${timestamp}`);
        break;

      case 'paused':
        setIsPaused(true);
        setStatus('Paused');
        break;

      case 'resumed':
        setIsPaused(false);
        setStatus('Playing');
        break;

      case 'stopped':
        setIsPlaying(false);
        setIsPaused(false);
        setCurrentBar(null);
        setStatus('Stopped');
        break;

      case 'finished':
        setIsPlaying(false);
        setIsPaused(false);
        setStatus('Replay Completed');
        break;

      case 'error':
        setStatus(`Error: ${data.message}`);
        setIsPlaying(false);
        setIsPaused(false);
        console.error('Replay error:', data.message);
        break;

      case 'heartbeat':
        // Keep connection alive
        break;

      default:
        console.log('Unknown message type:', data.type);
    }

    // Notify parent component of status change
    if (onReplayStatusChange) {
      onReplayStatusChange({
        isPlaying: data.type === 'bar' ? true : isPlaying,
        isPaused: data.type === 'paused',
        status: data.type,
        currentBar: data.bar || currentBar
      });
    }
  };

  const sendCommand = (command, additionalData = {}) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const message = {
        command,
        symbol,
        timeframe,
        speed,
        ...additionalData
      };

      console.log('Sending command:', message);
      wsRef.current.send(JSON.stringify(message));
      return true;
    } else {
      console.error('WebSocket not connected, state:', wsRef.current?.readyState);
      setStatus('Not Connected');
      return false;
    }
  };

  const formatDateTimeForBackend = (dateTimeLocal) => {
    if (!dateTimeLocal) return '';

    // Convert local datetime to ISO format with timezone
    const date = new Date(dateTimeLocal);

    // Get timezone offset in minutes and convert to hours:minutes format
    const offsetMinutes = date.getTimezoneOffset();
    const offsetHours = Math.floor(Math.abs(offsetMinutes) / 60);
    const offsetMins = Math.abs(offsetMinutes) % 60;
    const offsetSign = offsetMinutes <= 0 ? '+' : '-';
    const offsetString = `${offsetSign}${offsetHours.toString().padStart(2, '0')}:${offsetMins.toString().padStart(2, '0')}`;

    // Format as ISO string and replace 'Z' with timezone offset
    return date.toISOString().slice(0, -1) + offsetString;
  };

  const handlePlay = () => {
    if (!isConnected) {
      console.log('Not connected, attempting to connect...');
      connectWebSocket();
      setTimeout(() => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          handlePlay();
        }
      }, 1000);
      return;
    }

    const commandData = {};
    if (startDate) {
      // Format the datetime for the backend
      commandData.start_date = formatDateTimeForBackend(startDate);
    }

    if (sendCommand('start', commandData)) {
      setStatus('Starting replay...');
    }
  };

  const handlePause = () => {
    if (sendCommand('pause')) {
      setStatus('Pausing...');
    }
  };

  const handleResume = () => {
    if (sendCommand('resume')) {
      setStatus('Resuming...');
    }
  };

  const handleStop = () => {
    if (sendCommand('stop')) {
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
    if (isPlaying && !isPaused) {
      const commandData = {};
      if (startDate) {
        commandData.start_date = startDate;
      }
      sendCommand('start', commandData);
    }
  };

  return (
    <div className="replay-controls">
      <div className="controls-header">
        <h3>Replay Controls - {symbol} ({timeframe})</h3>
        <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
          {status}
        </div>
      </div>

      <div className="controls-row">
        {/* Date Selection */}
        <div className="control-group">
          <label htmlFor="start-date">Start Date & Time:</label>
          <input
            id="start-date"
            type="datetime-local"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            disabled={isPlaying && !isPaused}
          />
        </div>

        {/* Speed Selection */}
        <div className="control-group">
          <label htmlFor="speed">Speed:</label>
          <select
            id="speed"
            value={speed}
            onChange={(e) => handleSpeedChange(parseFloat(e.target.value))}
          >
            {speedOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="controls-row">
        {/* Playback Controls */}
        <div className="playback-controls">
          {!isPlaying ? (
            <button
              className="control-btn play-btn"
              onClick={handlePlay}
              disabled={!symbol}
            >
              ▶️ Play
            </button>
          ) : (
            <>
              {!isPaused ? (
                <button
                  className="control-btn pause-btn"
                  onClick={handlePause}
                >
                  ⏸️ Pause
                </button>
              ) : (
                <button
                  className="control-btn resume-btn"
                  onClick={handleResume}
                >
                  ▶️ Resume
                </button>
              )}
              <button
                className="control-btn stop-btn"
                onClick={handleStop}
              >
                ⏹️ Stop
              </button>
            </>
          )}

          {/* Connection status button */}
          {!isConnected && (
            <button
              className="control-btn connect-btn"
              onClick={connectWebSocket}
              disabled={wsRef.current?.readyState === WebSocket.CONNECTING}
            >
              🔄 Reconnect
            </button>
          )}
        </div>
      </div>

      {/* Current Bar Info */}
      {currentBar && (
        <div className="current-bar-info">
          <h4>Current Bar</h4>
          <div className="bar-details">
            <span>Time: {new Date(currentBar.timestamp).toLocaleString()}</span>
            <span>O: {currentBar.open.toFixed(4)}</span>
            <span>H: {currentBar.high.toFixed(4)}</span>
            <span>L: {currentBar.low.toFixed(4)}</span>
            <span>C: {currentBar.close.toFixed(4)}</span>
            <span>V: {currentBar.volume.toLocaleString()}</span>
          </div>
        </div>
      )}

      {/* Debug Info */}
      <div className="debug-info" style={{ fontSize: '12px', color: '#666', marginTop: '10px' }}>
        <div>WebSocket State: {wsRef.current?.readyState || 'null'}</div>
        <div>Connected: {isConnected.toString()}</div>
        <div>Playing: {isPlaying.toString()}</div>
        <div>Paused: {isPaused.toString()}</div>
      </div>
    </div>
  );
};

export default ReplayControls;