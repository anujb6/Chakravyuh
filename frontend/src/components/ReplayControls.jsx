// frontend/src/components/ReplayControls.js

import React, { useState, useEffect, useRef } from 'react';

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
    if (wsRef.current) {
      wsRef.current.close();
    }

    try {
      const wsUrl = `ws://localhost:8000/ws/replay/${symbol}`;
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        setIsConnected(true);
        setStatus('Connected');
        console.log('WebSocket connected for', symbol);
      };

      wsRef.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      };

      wsRef.current.onclose = () => {
        setIsConnected(false);
        setIsPlaying(false);
        setIsPaused(false);
        setStatus('Disconnected');
        console.log('WebSocket disconnected for', symbol);
        
        // Attempt to reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          if (symbol) {
            connectWebSocket();
          }
        }, 3000);
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setStatus('Connection Error');
      };

    } catch (error) {
      console.error('Error connecting WebSocket:', error);
      setStatus('Connection Failed');
    }
  };

  const disconnectWebSocket = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  };

  const handleWebSocketMessage = (data) => {
    switch (data.type) {
      case 'connected':
        setStatus('Ready for Replay');
        break;

      case 'bar':
        setCurrentBar(data.bar);
        if (onReplayData) {
          onReplayData(data.bar);
        }
        setStatus(`Playing - ${new Date(data.bar.timestamp).toLocaleString()}`);
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
        setStatus('Stopped');
        break;

      case 'finished':
        setIsPlaying(false);
        setIsPaused(false);
        setStatus('Replay Completed');
        break;

      case 'error':
        setStatus(`Error: ${data.message}`);
        break;

      case 'heartbeat':
        // Keep connection alive
        break;

      default:
        console.log('Unknown message type:', data.type);
    }

    if (onReplayStatusChange) {
      onReplayStatusChange({
        isPlaying,
        isPaused,
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
      
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.error('WebSocket not connected');
      setStatus('Not Connected');
    }
  };

  const handlePlay = () => {
    if (!isConnected) {
      connectWebSocket();
      return;
    }

    const commandData = {};
    if (startDate) {
      commandData.start_date = startDate;
    }

    sendCommand('start', commandData);
    setIsPlaying(true);
    setIsPaused(false);
  };

  const handlePause = () => {
    sendCommand('pause');
    setIsPaused(true);
  };

  const handleResume = () => {
    sendCommand('resume');
    setIsPaused(false);
  };

  const handleStop = () => {
    sendCommand('stop');
    setIsPlaying(false);
    setIsPaused(false);
    setCurrentBar(null);
  };

  const handleSpeedChange = (newSpeed) => {
    setSpeed(newSpeed);
    if (isPlaying && !isPaused) {
      sendCommand('start', { start_date: startDate });
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
          <label htmlFor="start-date">Start Date:</label>
          <input
            id="start-date"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            disabled={isPlaying}
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
    </div>
  );
};

export default ReplayControls;