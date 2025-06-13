// frontend/src/components/SymbolSelector.js

import React, { useState, useEffect } from 'react';
import axios from 'axios';

const SymbolSelector = ({ 
  selectedSymbol, 
  onSymbolChange, 
  disabled = false 
}) => {
  const [symbols, setSymbols] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  useEffect(() => {
    fetchSymbols();
  }, []);

  const fetchSymbols = async () => {
    try {
      setLoading(true);
      const response = await axios.get('https://chakravyuh.azurewebsites.net/commodities/symbols');
      
      if (response.data && Array.isArray(response.data)) {
        setSymbols(response.data);
        setError(null);
      } else {
        setError('Invalid response format');
      }
    } catch (err) {
      console.error('Error fetching symbols:', err);
      setError(err.response?.data?.detail || 'Failed to fetch symbols');
    } finally {
      setLoading(false);
    }
  };

  const filteredSymbols = symbols.filter(symbol =>
    symbol.symbol.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleSymbolSelect = (symbol) => {
    if (onSymbolChange) {
      onSymbolChange(symbol.symbol);
    }
    setIsDropdownOpen(false);
    setSearchTerm('');
  };

  const formatPrice = (price) => {
    return price.toFixed(4);
  };

  const formatDateRange = (dateRange) => {
    const start = new Date(dateRange.start).toLocaleDateString();
    const end = new Date(dateRange.end).toLocaleDateString();
    return `${start} - ${end}`;
  };

  if (loading) {
    return (
      <div className="symbol-selector loading">
        <div className="loading-spinner">Loading symbols...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="symbol-selector error">
        <div className="error-message">
          Error: {error}
          <button onClick={fetchSymbols} className="retry-btn">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="symbol-selector">
      <div className="selector-header">
        <h3>Select Symbol</h3>
        <div className="symbol-count">
          {symbols.length} symbols available
        </div>
      </div>

      {/* Current Selection Display */}
      {selectedSymbol && (
        <div className="current-selection">
          <div className="selected-symbol">
            <strong>{selectedSymbol}</strong>
            {symbols.find(s => s.symbol === selectedSymbol) && (
              <div className="symbol-details">
                <span>Last: ${formatPrice(symbols.find(s => s.symbol === selectedSymbol).last_price)}</span>
                <span>{symbols.find(s => s.symbol === selectedSymbol).total_bars.toLocaleString()} bars</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Symbol Dropdown */}
      <div className="dropdown-container">
        <div className="dropdown-header" onClick={() => !disabled && setIsDropdownOpen(!isDropdownOpen)}>
          <span>{selectedSymbol || 'Select a symbol...'}</span>
          <span className={`dropdown-arrow ${isDropdownOpen ? 'open' : ''}`}>▼</span>
        </div>

        {isDropdownOpen && !disabled && (
          <div className="dropdown-content">
            {/* Search Input */}
            <div className="search-container">
              <input
                type="text"
                placeholder="Search symbols..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="search-input"
              />
            </div>

            {/* Symbol List */}
            <div className="symbol-list">
              {filteredSymbols.length > 0 ? (
                filteredSymbols.map((symbol) => (
                  <div
                    key={symbol.symbol}
                    className={`symbol-item ${selectedSymbol === symbol.symbol ? 'selected' : ''}`}
                    onClick={() => handleSymbolSelect(symbol)}
                  >
                    <div className="symbol-info">
                      <div className="symbol-name">{symbol.symbol}</div>
                      <div className="symbol-meta">
                        <span className="price">${formatPrice(symbol.last_price)}</span>
                        <span className="bars">{symbol.total_bars.toLocaleString()} bars</span>
                      </div>
                      <div className="date-range">
                        {formatDateRange(symbol.date_range)}
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="no-results">
                  No symbols found matching "{searchTerm}"
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Symbol Statistics */}
      {selectedSymbol && symbols.find(s => s.symbol === selectedSymbol) && (
        <div className="symbol-stats">
          <h4>Symbol Information</h4>
          {(() => {
            const symbolData = symbols.find(s => s.symbol === selectedSymbol);
            return (
              <div className="stats-grid">
                <div className="stat-item">
                  <label>Symbol:</label>
                  <span>{symbolData.symbol}</span>
                </div>
                <div className="stat-item">
                  <label>Last Price:</label>
                  <span>${formatPrice(symbolData.last_price)}</span>
                </div>
                <div className="stat-item">
                  <label>Total Bars:</label>
                  <span>{symbolData.total_bars.toLocaleString()}</span>
                </div>
                <div className="stat-item">
                  <label>Date Range:</label>
                  <span>{formatDateRange(symbolData.date_range)}</span>
                </div>
                <div className="stat-item">
                  <label>Timeframes:</label>
                  <span>{symbolData.available_timeframes.join(', ')}</span>
                </div>
              </div>
            );
          })()}
        </div>
      )}
    </div>
  );
};

export default SymbolSelector;