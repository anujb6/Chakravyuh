// frontend/src/components/TradingChart.js
import React, { useEffect, useRef, useState, useCallback } from 'react';
import { createChart, ColorType } from 'lightweight-charts';
import './TradingChart.css';
import TimeframeDropdown from './TimeframeDropdown.jsx';
import PositionManager from './PositionManager.jsx';
import ChartManager from './ChartManager';

const TradingChart = ({
  symbol,
  timeframe,
  onTimeframeChange,
  isReplayMode = false,
  replayData = null,
  replayStartDate = null,
  positions = [],
  currentBar = null
}) => {
  const chartContainerRef = useRef();
  const chartManagerRef = useRef(null);
  const chartRef = useRef();
  const candlestickSeriesRef = useRef();
  const priceLinesRef = useRef([]);
  const positionLinesRef = useRef([]);
  const resizeObserverRef = useRef();

  const [internalPositions, setInternalPositions] = useState([]);
  const [showPositionManager, setShowPositionManager] = useState(false);
  const [positionManagerBalance, setPositionManagerBalance] = useState(10000);

  const [isTrendlineMode, setIsTrendlineMode] = useState(false);
  const [chartReady, setChartReady] = useState(false);
  const [historicalData, setHistoricalData] = useState([]);
  const [replayDataHistory, setReplayDataHistory] = useState([]);
  const [autoScroll, setAutoScroll] = useState(true);
  const [userInteracted, setUserInteracted] = useState(false);
  const [replayStartTime, setReplayStartTime] = useState(null);

  const timeframes = [
    { value: '1h', label: '1H' },
    { value: '2h', label: '2H' },
    { value: '4h', label: '4H' },
    { value: '1d', label: '1D' },
    { value: '1w', label: '1W' },
    { value: '1mo', label: '1M' }
  ];

  const handlePositionUpdate = useCallback((position) => {
    console.log('Position updated:', position);
  }, []);

  const handleBalanceUpdate = useCallback((newBalance, change) => {
    setPositionManagerBalance(newBalance);
    console.log('Balance updated:', newBalance, 'Change:', change);
  }, []);

  const handlePositionsChange = useCallback((newPositions) => {
    setInternalPositions(newPositions);
  }, []);

  const activePositions = positions.length > 0 ? positions : internalPositions;

  const addPositionMarkers = useCallback(() => {
    if (!candlestickSeriesRef.current || !activePositions.length) return;

    clearPositionEntryExitLines();

    const openPositions = activePositions.filter(position => position.status === 'open');

    openPositions.forEach(position => {
      const entryLineColor = position.type === 'buy' ? '#26a69a' : '#ef5350';
      const entryLine = {
        price: position.entryPrice,
        color: entryLineColor,
        lineWidth: 2,
        lineStyle: 0,
        axisLabelVisible: true,
        title: `${position.type.toUpperCase()} @ ${position.entryPrice.toFixed(4)}`
      };

      try {
        const priceLine = candlestickSeriesRef.current.createPriceLine(entryLine);
        positionLinesRef.current.push(priceLine);
      } catch (error) {
        console.log('Entry line creation failed:', error);
      }
    });

    if (openPositions.length === 0) {
      clearPositionEntryExitLines();
    }
  }, [activePositions]);

  const clearPositionLines = useCallback(() => {
    if (priceLinesRef.current.length > 0) {
      priceLinesRef.current.forEach(priceLine => {
        try {
          if (candlestickSeriesRef.current && priceLine) {
            candlestickSeriesRef.current.removePriceLine(priceLine);
          }
        } catch (error) {
          console.log('Error removing price line:', error);
        }
      });
      priceLinesRef.current = [];
    }
  }, []);

  const clearPositionEntryExitLines = useCallback(() => {
    if (positionLinesRef.current.length > 0) {
      positionLinesRef.current.forEach(priceLine => {
        try {
          if (candlestickSeriesRef.current && priceLine) {
            candlestickSeriesRef.current.removePriceLine(priceLine);
          }
        } catch (error) {
          console.log('Error removing position line:', error);
        }
      });
      positionLinesRef.current = [];
    }
  }, []);

  const addPositionLines = useCallback(() => {
    if (!chartRef.current || !candlestickSeriesRef.current) return;

    clearPositionLines();

    const openPositions = activePositions.filter(position => position.status === 'open');

    openPositions.forEach(position => {
      if (position.stopLoss) {
        const stopLossLine = {
          price: position.stopLoss,
          color: '#f44336',
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
          title: `SL: ${position.stopLoss.toFixed(4)}`
        };

        try {
          const priceLine = candlestickSeriesRef.current.createPriceLine(stopLossLine);
          priceLinesRef.current.push(priceLine);
        } catch (error) {
          console.log('Stop loss line creation failed:', error);
        }
      }

      if (position.takeProfit) {
        const takeProfitLine = {
          price: position.takeProfit,
          color: '#4caf50',
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
          title: `TP: ${position.takeProfit.toFixed(4)}`
        };

        try {
          const priceLine = candlestickSeriesRef.current.createPriceLine(takeProfitLine);
          priceLinesRef.current.push(priceLine);
        } catch (error) {
          console.log('Take profit line creation failed:', error);
        }
      }
    });

    if (openPositions.length === 0) {
      clearPositionLines();
    }
  }, [activePositions, clearPositionLines]);

  const handleResize = useCallback(() => {
    if (chartContainerRef.current && chartRef.current) {
      const { clientWidth, clientHeight } = chartContainerRef.current;
      chartRef.current.applyOptions({
        width: clientWidth,
        height: clientHeight,
      });
    }
  }, []);

  const handleChartInteraction = useCallback(() => {
    if (isReplayMode && !userInteracted) {
      setUserInteracted(true);
      setAutoScroll(false);
      console.log('User interacted with chart, auto-scroll disabled');
    }
  }, [isReplayMode, userInteracted]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Delete' || e.key === 'Backspace') {
        if (chartManagerRef.current) {
          chartManagerRef.current.deleteSelectedLine();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#0d1421' },
        textColor: '#d1d4dc',
      },
      grid: {
        vertLines: { color: '#1e2837' },
        horzLines: { color: '#1e2837' },
      },
      crosshair: {
        mode: 0,
        vertLine: {
          color: '#758696',
          width: 1,
          labelBackgroundColor: '#2a2a3e',
        },
        horzLine: {
          color: '#758696',
          width: 1,
          labelBackgroundColor: '#2a2a3e',
        },
      },
      rightPriceScale: {
        borderColor: '#2a2a3e',
        textColor: '#d1d4dc',
      },
      timeScale: {
        borderColor: '#2a2a3e',
        textColor: '#d1d4dc',
        timeVisible: true,
        secondsVisible: false,
      }
    });

    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
      priceFormat: {
        type: 'price',
        precision: 4,
        minMove: 0.0001,
      },
    });

    chartManagerRef.current = new ChartManager({
      chart,
      candleSeries: candlestickSeries,
      chartElement: chartContainerRef.current,
      onTrendlineComplete: () => {
        setIsTrendlineMode(false);
      },
    });

    chart.timeScale().subscribeVisibleTimeRangeChange(handleChartInteraction);
    chart.subscribeCrosshairMove(handleChartInteraction);

    if (chartContainerRef.current) {
      chartContainerRef.current.addEventListener('wheel', handleChartInteraction);
      chartContainerRef.current.addEventListener('mousedown', handleChartInteraction);
      chartContainerRef.current.addEventListener('touchstart', handleChartInteraction);
    }

    chartRef.current = chart;
    candlestickSeriesRef.current = candlestickSeries;
    setChartReady(true);

    setTimeout(handleResize, 100);

    if (window.ResizeObserver) {
      resizeObserverRef.current = new ResizeObserver(entries => {
        requestAnimationFrame(() => {
          handleResize();
        });
      });
      resizeObserverRef.current.observe(chartContainerRef.current);
    }

    window.addEventListener('resize', handleResize);

    return () => {
      clearPositionLines();
      clearPositionEntryExitLines();

      window.removeEventListener('resize', handleResize);

      if (chartContainerRef.current) {
        chartContainerRef.current.removeEventListener('wheel', handleChartInteraction);
        chartContainerRef.current.removeEventListener('mousedown', handleChartInteraction);
        chartContainerRef.current.removeEventListener('touchstart', handleChartInteraction);
      }

      if (resizeObserverRef.current) {
        resizeObserverRef.current.disconnect();
      }

      if (chart) {
        chart.remove();
      }
    };
  }, [symbol, handleResize, handleChartInteraction, clearPositionLines]);

  useEffect(() => {
    if (chartReady && activePositions) {
      addPositionMarkers();
      addPositionLines();
    }
  }, [chartReady, activePositions, addPositionMarkers, addPositionLines]);

  useEffect(() => {
    if (!chartReady) return;

    const timeoutId = setTimeout(() => {
      handleResize();
    }, 50);

    return () => clearTimeout(timeoutId);
  }, [chartReady, handleResize]);

  useEffect(() => {
    if (!chartReady || !symbol || !timeframe) return;

    console.log('Fetching chart data for:', symbol, timeframe);
    fetchChartData();
  }, [chartReady, symbol, timeframe]);

  useEffect(() => {
    if (!chartReady || !isReplayMode) {
      if (!isReplayMode && historicalData.length > 0) {
        console.log('Exiting replay mode, showing full historical data');
        updateChart(historicalData);
      }
      return;
    }

    console.log('Initializing replay mode');
    setAutoScroll(true);
    setUserInteracted(false);
    setReplayDataHistory([]);
  }, [chartReady, isReplayMode, historicalData]);

  useEffect(() => {
    if (!chartReady || !isReplayMode || !replayStartDate || !historicalData.length) return;

    console.log('Setting up replay with start date:', replayStartDate);

    const startTime = new Date(replayStartDate).getTime();
    setReplayStartTime(startTime);

    const preReplayData = historicalData.filter(bar => {
      const barTime = new Date(bar.time).getTime();
      return barTime < startTime;
    });

    console.log(`Showing ${preReplayData.length} historical bars before replay start`);

    updateChart(preReplayData);

    if (chartRef.current && preReplayData.length > 0) {
      setTimeout(() => {
        chartRef.current.timeScale().scrollToRealTime();
      }, 100);
    }
  }, [chartReady, isReplayMode, replayStartDate, historicalData]);

  useEffect(() => {
    if (!chartReady || !isReplayMode || !replayData) return;

    console.log('Updating chart with replay data:', replayData);
    updateChartWithReplayData(replayData);
  }, [chartReady, isReplayMode, replayData]);

  const fetchChartData = async () => {
    try {
      const response = await fetch(`http://localhost:8000/commodities/${symbol}?timeframe=${timeframe}`);
      const data = await response.json();

      if (data && data.data) {
        console.log('Fetched chart data:', data.data.length, 'bars');
        setHistoricalData(data.data);
        if (!isReplayMode) {
          updateChart(data.data);
        }
      }
    } catch (error) {
      console.error('Error fetching chart data:', error);
    }
  };

  const updateChart = useCallback((data) => {
    if (!candlestickSeriesRef.current || !data.length) return;

    const candlestickData = data.map(bar => ({
      time: new Date(bar.time).getTime() / 1000,
      open: bar.open,
      high: bar.high,
      low: bar.low,
      close: bar.close,
    }));

    candlestickSeriesRef.current.setData(candlestickData);
    if (chartRef.current) {
      chartRef.current.timeScale().fitContent();
    }

    setTimeout(handleResize, 100);
  }, [handleResize]);

  const updateChartWithReplayData = useCallback((barData) => {
    if (!candlestickSeriesRef.current) return;

    console.log('Processing replay bar:', barData);

    const time = new Date(barData.timestamp).getTime() / 1000;

    setReplayDataHistory(prev => {
      const newHistory = [...prev, barData];
      return newHistory;
    });

    const candlestickBar = {
      time: time,
      open: barData.open,
      high: barData.high,
      low: barData.low,
      close: barData.close,
    };

    try {
      candlestickSeriesRef.current.update(candlestickBar);

      if (chartRef.current && autoScroll && !userInteracted) {
        chartRef.current.timeScale().scrollToRealTime();
      }

      console.log('Successfully updated chart with replay data');
    } catch (error) {
      console.error('Error updating chart with replay data:', error);
    }
  }, [autoScroll, userInteracted]);

  const handleTimeframeClick = (newTimeframe) => {
    if (newTimeframe !== timeframe && onTimeframeChange) {
      onTimeframeChange(newTimeframe);
    }
  };

  const togglePositionManager = () => {
    setShowPositionManager(!showPositionManager);
  };

  return (
    <div className="trading-chart-maximized">
      {/* Top Toolbar */}
      <div className="chart-toolbar">
        <div className="toolbar-left">
          <TimeframeDropdown
            timeframes={timeframes}
            timeframe={timeframe}
            handleTimeframeClick={handleTimeframeClick}
            isReplayMode={isReplayMode}
          />

          <button
            className={`trendline-toggle ${isTrendlineMode ? 'active' : ''}`}
            onClick={() => {
              setIsTrendlineMode(true);
              if (chartManagerRef.current) {
                chartManagerRef.current.setTrendlineMode(true);
              }
            }}
            title="Draw Trendline"
          >
            ✏️ Draw Trendline
          </button>

          {/* Position Manager Toggle */}
          <button
            className={`position-manager-toggle ${showPositionManager ? 'active' : ''}`}
            onClick={togglePositionManager}
            title="Toggle Position Manager"
          >
            <span className="icon">📈</span>
            <span>Positions</span>
          </button>
        </div>

        <div className="toolbar-right">
          {isReplayMode && activePositions && activePositions.length > 0 && (
            <div className="chart-position-summary">
              <span className="position-count">
                Positions: {activePositions.filter(p => p.status === 'open').length} open, {activePositions.filter(p => p.status === 'closed').length} closed
              </span>
              <span className="balance-display">
                Balance: ${positionManagerBalance.toFixed(2)}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="chart-content-area">
        {/* Chart Container */}
        <div
          ref={chartContainerRef}
          className="chart-container-maximized"
        />

        {/* Position Manager Panel*/}
        <div
          className="position-manager-panel"
          style={{
            display: showPositionManager ? 'flex' : 'none',
            flexDirection: 'column'
          }}
        >
          <div className="panel-header">
            <h3>Position Manager</h3>
            <button
              className="panel-close"
              onClick={() => setShowPositionManager(false)}
              title="Close Panel"
            >
              ✕
            </button>
          </div>
          <div className="panel-content">
            <PositionManager
              currentBar={currentBar}
              isReplayMode={isReplayMode}
              onPositionUpdate={handlePositionUpdate}
              onBalanceUpdate={handleBalanceUpdate}
              onPositionsChange={handlePositionsChange}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default TradingChart;