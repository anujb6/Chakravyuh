// frontend/src/components/PositionManager.js
import React, { useState, useEffect, useCallback } from 'react';
import './PositionManager.css';

const PositionManager = ({
  currentBar,
  isReplayMode,
  onPositionUpdate,
  onBalanceUpdate,
  onPositionsChange
}) => {
  const [positions, setPositions] = useState([]);
  const [balance, setBalance] = useState(10000); // Starting balance
  const [showOrderForm, setShowOrderForm] = useState(false);
  const [orderType, setOrderType] = useState('buy'); // 'buy' or 'sell'
  const [orderSize, setOrderSize] = useState(100);
  const [stopLoss, setStopLoss] = useState('');
  const [takeProfit, setTakeProfit] = useState('');
  const [unrealizedPnL, setUnrealizedPnL] = useState(0);
  const [totalPnL, setTotalPnL] = useState(0);

  // Pass positions to parent whenever they change
  useEffect(() => {
    if (onPositionsChange) {
      onPositionsChange(positions);
    }
  }, [positions, onPositionsChange]);

  // Calculate unrealized P&L for open positions
  useEffect(() => {
    if (!currentBar || !positions.length) {
      setUnrealizedPnL(0);
      return;
    }

    const currentPrice = currentBar.close;
    let unrealized = 0;

    positions.forEach(position => {
      if (position.status === 'open') {
        const pnl = position.type === 'buy' 
          ? (currentPrice - position.entryPrice) * position.size
          : (position.entryPrice - currentPrice) * position.size;
        unrealized += pnl;
      }
    });

    setUnrealizedPnL(unrealized);
  }, [currentBar, positions]);

  // Check stop-loss and take-profit triggers
  useEffect(() => {
    if (!currentBar || !positions.length) return;

    const currentPrice = currentBar.close;
    const currentTime = new Date(currentBar.timestamp);

    setPositions(prevPositions => {
      let updatedPositions = [...prevPositions];
      let balanceChange = 0;

      updatedPositions.forEach((position, index) => {
        if (position.status !== 'open') return;

        let shouldClose = false;
        let closeReason = '';
        let closePrice = currentPrice;

        // Check Stop Loss
        if (position.stopLoss) {
          const slTriggered = position.type === 'buy' 
            ? currentPrice <= position.stopLoss
            : currentPrice >= position.stopLoss;
          
          if (slTriggered) {
            shouldClose = true;
            closeReason = 'Stop Loss';
            closePrice = position.stopLoss;
          }
        }

        // Check Take Profit
        if (!shouldClose && position.takeProfit) {
          const tpTriggered = position.type === 'buy'
            ? currentPrice >= position.takeProfit
            : currentPrice <= position.takeProfit;
          
          if (tpTriggered) {
            shouldClose = true;
            closeReason = 'Take Profit';
            closePrice = position.takeProfit;
          }
        }

        // Close position if triggered
        if (shouldClose) {
          const pnl = position.type === 'buy'
            ? (closePrice - position.entryPrice) * position.size
            : (position.entryPrice - closePrice) * position.size;

          updatedPositions[index] = {
            ...position,
            status: 'closed',
            exitPrice: closePrice,
            exitTime: currentTime.toISOString(),
            pnl: pnl,
            closeReason: closeReason
          };

          balanceChange += pnl;
        }
      });

      // Update balance if there were any closed positions
      if (balanceChange !== 0) {
        setBalance(prev => {
          const newBalance = prev + balanceChange;
          setTotalPnL(prev => prev + balanceChange);
          if (onBalanceUpdate) {
            onBalanceUpdate(newBalance, balanceChange);
          }
          return newBalance;
        });
      }

      return updatedPositions;
    });
  }, [currentBar, onBalanceUpdate]);

  const openPosition = useCallback(() => {
    if (!currentBar || !isReplayMode) return;

    const currentPrice = currentBar.close;
    const currentTime = new Date(currentBar.timestamp);
    
    // Validate order size doesn't exceed balance
    const requiredMargin = orderSize * currentPrice * 0.1; // 10% margin requirement
    if (requiredMargin > balance) {
      alert('Insufficient balance for this position size');
      return;
    }

    const newPosition = {
      id: Date.now() + Math.random(),
      type: orderType,
      size: orderSize,
      entryPrice: currentPrice,
      entryTime: currentTime.toISOString(),
      stopLoss: stopLoss ? parseFloat(stopLoss) : null,
      takeProfit: takeProfit ? parseFloat(takeProfit) : null,
      status: 'open',
      pnl: 0,
      closeReason: null,
      exitPrice: null,
      exitTime: null
    };

    setPositions(prev => [...prev, newPosition]);
    setShowOrderForm(false);
    setStopLoss('');
    setTakeProfit('');

    if (onPositionUpdate) {
      onPositionUpdate(newPosition);
    }
  }, [currentBar, isReplayMode, orderType, orderSize, stopLoss, takeProfit, balance, onPositionUpdate]);

  const closePosition = useCallback((positionId) => {
    if (!currentBar) return;

    const currentPrice = currentBar.close;
    const currentTime = new Date(currentBar.timestamp);

    setPositions(prev => {
      const updatedPositions = prev.map(position => {
        if (position.id === positionId && position.status === 'open') {
          const pnl = position.type === 'buy'
            ? (currentPrice - position.entryPrice) * position.size
            : (position.entryPrice - currentPrice) * position.size;

          // Update balance
          setBalance(prevBalance => {
            const newBalance = prevBalance + pnl;
            setTotalPnL(prevTotal => prevTotal + pnl);
            if (onBalanceUpdate) {
              onBalanceUpdate(newBalance, pnl);
            }
            return newBalance;
          });

          return {
            ...position,
            status: 'closed',
            exitPrice: currentPrice,
            exitTime: currentTime.toISOString(),
            pnl: pnl,
            closeReason: 'Manual Close'
          };
        }
        return position;
      });

      return updatedPositions;
    });
  }, [currentBar, onBalanceUpdate]);

  const clearAllPositions = useCallback(() => {
    setPositions([]);
    setBalance(10000);
    setTotalPnL(0);
    setUnrealizedPnL(0);
  }, []);

  const openPositions = positions.filter(p => p.status === 'open');
  const closedPositions = positions.filter(p => p.status === 'closed');

  return (
    <div className="position-manager">
      {/* Account Summary */}
      <div className="account-summary">
        <h4>Account</h4>
        <div className="summary-grid">
          <div className="summary-item">
            <span>Balance:</span>
            <span className="balance">${balance.toFixed(2)}</span>
          </div>
          <div className="summary-item">
            <span>Unrealized P&L:</span>
            <span className={`pnl ${unrealizedPnL >= 0 ? 'positive' : 'negative'}`}>
              ${unrealizedPnL.toFixed(2)}
            </span>
          </div>
          <div className="summary-item">
            <span>Total P&L:</span>
            <span className={`pnl ${totalPnL >= 0 ? 'positive' : 'negative'}`}>
              ${totalPnL.toFixed(2)}
            </span>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="quick-actions">
        <button
          className="action-btn buy"
          onClick={() => {
            setOrderType('buy');
            setShowOrderForm(true);
          }}
          disabled={!isReplayMode || !currentBar}
        >
          🟢 Buy
        </button>
        <button
          className="action-btn sell"
          onClick={() => {
            setOrderType('sell');
            setShowOrderForm(true);
          }}
          disabled={!isReplayMode || !currentBar}
        >
          🔴 Sell
        </button>
        <button
          className="action-btn clear"
          onClick={clearAllPositions}
        >
          🗑️ Clear All
        </button>
      </div>

      {/* Order Form */}
      {showOrderForm && (
        <div className="order-form">
          <h4>New {orderType.toUpperCase()} Order</h4>
          <div className="form-grid">
            <div className="form-group">
              <label>Size:</label>
              <input
                type="number"
                value={orderSize}
                onChange={(e) => setOrderSize(Number(e.target.value))}
                min="1"
                step="1"
              />
            </div>
            <div className="form-group">
              <label>Stop Loss:</label>
              <input
                type="number"
                value={stopLoss}
                onChange={(e) => setStopLoss(e.target.value)}
                step="0.0001"
                placeholder="Optional"
              />
            </div>
            <div className="form-group">
              <label>Take Profit:</label>
              <input
                type="number"
                value={takeProfit}
                onChange={(e) => setTakeProfit(e.target.value)}
                step="0.0001"
                placeholder="Optional"
              />
            </div>
          </div>
          <div className="form-actions">
            <button
              className="confirm-btn"
              onClick={openPosition}
            >
              Confirm Order
            </button>
            <button
              className="cancel-btn"
              onClick={() => setShowOrderForm(false)}
            >
              Cancel
            </button>
          </div>
          {currentBar && (
            <div className="current-price">
              Current Price: ${currentBar.close.toFixed(4)}
            </div>
          )}
        </div>
      )}

      {/* Open Positions */}
      {openPositions.length > 0 && (
        <div className="positions-section">
          <h4>Open Positions ({openPositions.length})</h4>
          <div className="positions-list">
            {openPositions.map(position => {
              const currentPnL = currentBar ? (
                position.type === 'buy'
                  ? (currentBar.close - position.entryPrice) * position.size
                  : (position.entryPrice - currentBar.close) * position.size
              ) : 0;

              return (
                <div key={position.id} className="position-card open">
                  <div className="position-header">
                    <span className={`position-type ${position.type}`}>
                      {position.type.toUpperCase()}
                    </span>
                    <span className="position-size">Size: {position.size}</span>
                    <button
                      className="close-btn"
                      onClick={() => closePosition(position.id)}
                      title="Close Position"
                    >
                      ✕
                    </button>
                  </div>
                  <div className="position-details">
                    <div className="detail-row">
                      <span>Entry:</span>
                      <span>${position.entryPrice.toFixed(4)}</span>
                    </div>
                    {currentBar && (
                      <div className="detail-row">
                        <span>Current:</span>
                        <span>${currentBar.close.toFixed(4)}</span>
                      </div>
                    )}
                    <div className="detail-row">
                      <span>P&L:</span>
                      <span className={`pnl ${currentPnL >= 0 ? 'positive' : 'negative'}`}>
                        ${currentPnL.toFixed(2)}
                      </span>
                    </div>
                    {position.stopLoss && (
                      <div className="detail-row">
                        <span>Stop Loss:</span>
                        <span className="sl">${position.stopLoss.toFixed(4)}</span>
                      </div>
                    )}
                    {position.takeProfit && (
                      <div className="detail-row">
                        <span>Take Profit:</span>
                        <span className="tp">${position.takeProfit.toFixed(4)}</span>
                      </div>
                    )}
                  </div>
                  <div className="position-time">
                    Opened: {new Date(position.entryTime).toLocaleString()}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Closed Positions History */}
      {closedPositions.length > 0 && (
        <div className="positions-section">
          <details>
            <summary>Position History ({closedPositions.length})</summary>
            <div className="positions-list">
              {closedPositions.slice(-10).reverse().map(position => (
                <div key={position.id} className="position-card closed">
                  <div className="position-header">
                    <span className={`position-type ${position.type}`}>
                      {position.type.toUpperCase()}
                    </span>
                    <span className="position-size">Size: {position.size}</span>
                    <span className="close-reason">{position.closeReason}</span>
                  </div>
                  <div className="position-details">
                    <div className="detail-row">
                      <span>Entry:</span>
                      <span>${position.entryPrice.toFixed(4)}</span>
                    </div>
                    <div className="detail-row">
                      <span>Exit:</span>
                      <span>${position.exitPrice.toFixed(4)}</span>
                    </div>
                    <div className="detail-row">
                      <span>P&L:</span>
                      <span className={`pnl ${position.pnl >= 0 ? 'positive' : 'negative'}`}>
                        ${position.pnl.toFixed(2)}
                      </span>
                    </div>
                  </div>
                  <div className="position-time">
                    {new Date(position.entryTime).toLocaleDateString()} - {new Date(position.exitTime).toLocaleDateString()}
                  </div>
                </div>
              ))}
            </div>
          </details>
        </div>
      )}

      {!isReplayMode && (
        <div className="disabled-notice">
          Position trading is only available in replay mode
        </div>
      )}
    </div>
  );
};

export default PositionManager;