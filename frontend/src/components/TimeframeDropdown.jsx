import React, { useState, useRef, useEffect } from 'react';
import './TimeframeDropdown.css';

const TimeframeDropdown = ({ 
  timeframes, 
  timeframe, 
  handleTimeframeClick, 
  isReplayMode 
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  
  const primaryTimeframes = timeframes.slice(0, 3);
  const dropdownTimeframes = timeframes.slice(3);
  
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);
  
  const handleDropdownItemClick = (value) => {
    handleTimeframeClick(value);
    setIsOpen(false);
  };
  
  return (
    <div className="timeframe-bar">
      <div className="timeframe-selector-compact">
        {/* Primary timeframes always visible */}
        {primaryTimeframes.map((tf) => (
          <button
            key={tf.value}
            className={`timeframe-btn-compact ${timeframe === tf.value ? 'active' : ''}`}
            onClick={() => handleTimeframeClick(tf.value)}
            disabled={isReplayMode}
          >
            {tf.label}
          </button>
        ))}
        
        {/* Dropdown for additional timeframes */}
        {dropdownTimeframes.length > 0 && (
          <div className="timeframe-dropdown" ref={dropdownRef}>
            <button
              className={`timeframe-btn-compact dropdown-trigger ${
                dropdownTimeframes.some(tf => tf.value === timeframe) ? 'active' : ''
              }`}
              onClick={() => setIsOpen(!isOpen)}
              disabled={isReplayMode}
            >
              {dropdownTimeframes.find(tf => tf.value === timeframe)?.label || '⋯'}
              <span className="dropdown-arrow">▼</span>
            </button>
            
            {isOpen && (
              <div className="timeframe-dropdown-menu">
                {dropdownTimeframes.map((tf) => (
                  <button
                    key={tf.value}
                    className={`timeframe-dropdown-item ${timeframe === tf.value ? 'active' : ''}`}
                    onClick={() => handleDropdownItemClick(tf.value)}
                    disabled={isReplayMode}
                  >
                    {tf.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default TimeframeDropdown;