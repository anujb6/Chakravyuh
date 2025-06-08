// frontend/src/components/TradingChart.js
import React, { useEffect, useRef, useState, useCallback } from 'react';
import { createChart, ColorType } from 'lightweight-charts';
import './TradingChart.css';
import TimeframeDropdown from './TimeframeDropdown.jsx';

const TradingChart = ({
  symbol,
  timeframe,
  onTimeframeChange,
  isReplayMode = false,
  replayData = null,
  replayStartDate = null,
  positions = [], // Add positions prop
  currentBar = null // Add currentBar prop
}) => {
  const chartContainerRef = useRef();
  const chartRef = useRef();
  const candlestickSeriesRef = useRef();
  const positionMarkersRef = useRef([]);
  const priceLinesRef = useRef([]); // Add reference to track price lines
  const positionLinesRef = useRef([]); // Add reference to track position entry/exit lines
  const resizeObserverRef = useRef();
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

  const addPositionMarkers = useCallback(() => {
    if (!candlestickSeriesRef.current || !positions.length) return;

    // Clear existing position lines
    clearPositionEntryExitLines();

    // Only add markers for OPEN positions
    const openPositions = positions.filter(position => position.status === 'open');

    openPositions.forEach(position => {
      // Add entry line (green for buy, red for sell)
      const entryLineColor = position.type === 'buy' ? '#26a69a' : '#ef5350';
      const entryLine = {
        price: position.entryPrice,
        color: entryLineColor,
        lineWidth: 2,
        lineStyle: 0, // Solid line
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

    // If there are no open positions, clear all markers
    if (openPositions.length === 0) {
      clearPositionEntryExitLines();
    }
  }, [positions]);

  // Clear existing price lines
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

  // Clear position entry/exit lines
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

    // Clear existing price lines first
    clearPositionLines();

    // Only add lines for OPEN positions
    const openPositions = positions.filter(position => position.status === 'open');

    openPositions.forEach(position => {
      // Add stop loss line
      if (position.stopLoss) {
        const stopLossLine = {
          price: position.stopLoss,
          color: '#f44336',
          lineWidth: 1,
          lineStyle: 2, // Dashed
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

      // Add take profit line
      if (position.takeProfit) {
        const takeProfitLine = {
          price: position.takeProfit,
          color: '#4caf50',
          lineWidth: 1,
          lineStyle: 2, // Dashed
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

    // If there are no open positions, clear all lines
    if (openPositions.length === 0) {
      clearPositionLines();
    }
  }, [positions, clearPositionLines]);

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
        mode: 1,
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
    if (chartReady && positions) {
      addPositionMarkers();
      addPositionLines();
    }
  }, [chartReady, positions, addPositionMarkers, addPositionLines]);

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

  return (
    <div className="trading-chart-maximized">
      {/* Timeframe Selector */}
      <div className="timeframe-bar">
        <TimeframeDropdown
          timeframes={timeframes}
          timeframe={timeframe}
          handleTimeframeClick={handleTimeframeClick}
          isReplayMode={isReplayMode}
        />
        {isReplayMode && positions && positions.length > 0 && (
          <div className="chart-position-summary">
            <span className="position-count">
              Positions: {positions.filter(p => p.status === 'open').length} open, {positions.filter(p => p.status === 'closed').length} closed
            </span>
          </div>
        )}
      </div>

      {/* Chart Container */}
      <div
        ref={chartContainerRef}
        className="chart-container-maximized"
      />
    </div>
  );
};

export default TradingChart;