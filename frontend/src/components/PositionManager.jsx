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
  const [balance, setBalance] = useState(10000);
  const [showOrderForm, setShowOrderForm] = useState(false);
  const [orderType, setOrderType] = useState('buy');
  const [orderSize, setOrderSize] = useState(1);
  const [stopLoss, setStopLoss] = useState('');
  const [takeProfit, setTakeProfit] = useState('');
  const [unrealizedPnL, setUnrealizedPnL] = useState(0);
  const [totalPnL, setTotalPnL] = useState(0);

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
        const pnl = calculatePnL(position, currentPrice);
        unrealized += pnl;
      }
    });

    setUnrealizedPnL(unrealized);
  }, [currentBar, positions]);

  // Helper function to calculate P&L consistently
  const calculatePnL = (position, currentPrice) => {
    if (position.type === 'buy') {
      return (currentPrice - position.entryPrice) * position.size;
    } else {
      return (position.entryPrice - currentPrice) * position.size;
    }
  };

  // Handle stop loss and take profit triggers
  useEffect(() => {
    if (!currentBar || !positions.length) return;

    const currentPrice = currentBar.close;
    const currentTime = new Date(currentBar.timestamp);

    setPositions(prevPositions => {
      let updatedPositions = [...prevPositions];
      let totalBalanceChange = 0;

      updatedPositions.forEach((position, index) => {
        if (position.status !== 'open') return;

        let shouldClose = false;
        let closeReason = '';
        let closePrice = currentPrice;

        // Check stop loss
        if (position.stopLoss !== null && position.stopLoss !== undefined) {
          const slTriggered = position.type === 'buy' 
            ? currentPrice <= position.stopLoss
            : currentPrice >= position.stopLoss;
          
          if (slTriggered) {
            shouldClose = true;
            closeReason = 'Stop Loss';
            closePrice = position.stopLoss;
          }
        }

        // Check take profit (only if stop loss hasn't triggered)
        if (!shouldClose && position.takeProfit !== null && position.takeProfit !== undefined) {
          const tpTriggered = position.type === 'buy'
            ? currentPrice >= position.takeProfit
            : currentPrice <= position.takeProfit;
          
          if (tpTriggered) {
            shouldClose = true;
            closeReason = 'Take Profit';
            closePrice = position.takeProfit;
          }
        }

        if (shouldClose) {
          const pnl = calculatePnL({...position, entryPrice: position.entryPrice}, closePrice);

          updatedPositions[index] = {
            ...position,
            status: 'closed',
            exitPrice: closePrice,
            exitTime: currentTime.toISOString(),
            pnl: pnl,
            closeReason: closeReason
          };

          totalBalanceChange += pnl;
        }
      });

      // Update balance and total P&L if there were any position closures
      if (totalBalanceChange !== 0) {
        setBalance(prev => {
          const newBalance = prev + totalBalanceChange;
          if (onBalanceUpdate) {
            onBalanceUpdate(newBalance, totalBalanceChange);
          }
          return newBalance;
        });
        
        setTotalPnL(prev => prev + totalBalanceChange);
      }

      return updatedPositions;
    });
  }, [currentBar, onBalanceUpdate]);

  const openPosition = useCallback(() => {
    if (!currentBar || !isReplayMode) return;

    const currentPrice = currentBar.close;
    const currentTime = new Date(currentBar.timestamp);
    
    // Calculate required margin (10% of position value)
    const positionValue = orderSize * currentPrice;
    const requiredMargin = positionValue * 0.1;
    
    if (requiredMargin > balance) {
      alert(`Insufficient balance. Required: $${requiredMargin.toFixed(2)}, Available: $${balance.toFixed(2)}`);
      return;
    }

    // Validate stop loss and take profit levels
    const parsedStopLoss = stopLoss ? parseFloat(stopLoss) : null;
    const parsedTakeProfit = takeProfit ? parseFloat(takeProfit) : null;

    // Basic validation for stop loss and take profit levels
    if (orderType === 'buy') {
      if (parsedStopLoss && parsedStopLoss >= currentPrice) {
        alert('Stop loss must be below current price for buy orders');
        return;
      }
      if (parsedTakeProfit && parsedTakeProfit <= currentPrice) {
        alert('Take profit must be above current price for buy orders');
        return;
      }
    } else {
      if (parsedStopLoss && parsedStopLoss <= currentPrice) {
        alert('Stop loss must be above current price for sell orders');
        return;
      }
      if (parsedTakeProfit && parsedTakeProfit >= currentPrice) {
        alert('Take profit must be below current price for sell orders');
        return;
      }
    }

    const newPosition = {
      id: Date.now() + Math.random(),
      type: orderType,
      size: orderSize,
      entryPrice: currentPrice,
      entryTime: currentTime.toISOString(),
      stopLoss: parsedStopLoss,
      takeProfit: parsedTakeProfit,
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
          const pnl = calculatePnL(position, currentPrice);

          // Update balance and total P&L
          setBalance(prevBalance => {
            const newBalance = prevBalance + pnl;
            if (onBalanceUpdate) {
              onBalanceUpdate(newBalance, pnl);
            }
            return newBalance;
          });

          setTotalPnL(prevTotal => prevTotal + pnl);

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
          <div className="summary-item">
            <span>Equity:</span>
            <span className="equity">${(balance + unrealizedPnL).toFixed(2)}</span>
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
          🗑️ Clear
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
                onChange={(e) => setOrderSize(Math.max(1, Number(e.target.value)))}
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
              {orderSize && (
                <div className="position-info">
                  Position Value: ${(orderSize * currentBar.close).toFixed(2)} | 
                  Required Margin: ${(orderSize * currentBar.close * 0.1).toFixed(2)}
                </div>
              )}
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
              const currentPnL = currentBar ? calculatePnL(position, currentBar.close) : 0;

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
                    {position.stopLoss !== null && position.stopLoss !== undefined && (
                      <div className="detail-row">
                        <span>Stop Loss:</span>
                        <span className="sl">${position.stopLoss.toFixed(4)}</span>
                      </div>
                    )}
                    {position.takeProfit !== null && position.takeProfit !== undefined && (
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