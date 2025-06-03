// frontend/src/components/TradingChart.js

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { createChart, ColorType } from 'lightweight-charts';
import './TradingChart.css'; // Import your CSS styles
import TimeframeDropdown from './TimeframeDropdown.jsx';

const TradingChart = ({
  symbol,
  timeframe,
  onTimeframeChange,
  isReplayMode = false,
  replayData = null
}) => {
  const chartContainerRef = useRef();
  const chartRef = useRef();
  const candlestickSeriesRef = useRef();
  const volumeSeriesRef = useRef();
  const resizeObserverRef = useRef();
  const resizeObserverRef = useRef();
  const [chartReady, setChartReady] = useState(false);
  const [replayDataHistory, setReplayDataHistory] = useState([]);
  const [autoScroll, setAutoScroll] = useState(true); // New state for auto-scroll control
  const [userInteracted, setUserInteracted] = useState(false); // Track user interaction

  // Available timeframes
  const timeframes = [
    { value: '1h', label: '1H' },
    { value: '4h', label: '4H' },
    { value: '1d', label: '1D' },
    { value: '1w', label: '1W' },
    { value: '1mo', label: '1M' }
  ];

  // Resize handler function
  const handleResize = useCallback(() => {
    if (chartContainerRef.current && chartRef.current) {
      const { clientWidth, clientHeight } = chartContainerRef.current;
      chartRef.current.applyOptions({
        width: clientWidth,
        height: clientHeight,
      });
    }
  }, []);

  // Handle user interaction with chart
  const handleChartInteraction = useCallback(() => {
    if (isReplayMode && !userInteracted) {
      setUserInteracted(true);
      setAutoScroll(false);
      console.log('User interacted with chart, auto-scroll disabled');
    }
  }, [isReplayMode, userInteracted]);

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#0d1421' },
        background: { type: ColorType.Solid, color: '#0d1421' },
        textColor: '#d1d4dc',
      },
      grid: {
        vertLines: { color: '#1e2837' },
        horzLines: { color: '#1e2837' },
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
        borderColor: '#2a2a3e',
        textColor: '#d1d4dc',
      },
      timeScale: {
        borderColor: '#2a2a3e',
        textColor: '#d1d4dc',
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
      priceFormat: {
        type: 'price',
        precision: 4,
        minMove: 0.0001,
      },
    });

    const volumeSeries = chart.addHistogramSeries({
      color: '#26a69a',
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: 'volume',
    });

    chart.priceScale('volume').applyOptions({
      scaleMargins: {
        top: 0.85,
        top: 0.85,
        bottom: 0,
      },
      textColor: '#888',
      textColor: '#888',
    });

    // Add event listeners to detect user interaction
    chart.timeScale().subscribeVisibleTimeRangeChange(handleChartInteraction);
    chart.subscribeCrosshairMove(handleChartInteraction);
    
    // Add mouse event listeners to the chart container
    if (chartContainerRef.current) {
      chartContainerRef.current.addEventListener('wheel', handleChartInteraction);
      chartContainerRef.current.addEventListener('mousedown', handleChartInteraction);
      chartContainerRef.current.addEventListener('touchstart', handleChartInteraction);
    }

    chartRef.current = chart;
    candlestickSeriesRef.current = candlestickSeries;
    volumeSeriesRef.current = volumeSeries;
    setChartReady(true);

    // Initial resize
    setTimeout(handleResize, 100);

    // Set up ResizeObserver for better resize detection
    if (window.ResizeObserver) {
      resizeObserverRef.current = new ResizeObserver(entries => {
        // Use requestAnimationFrame to debounce resize calls
        requestAnimationFrame(() => {
          handleResize();
        });
      });
      resizeObserverRef.current.observe(chartContainerRef.current);
    }

    // Fallback to window resize event
    // Initial resize
    setTimeout(handleResize, 100);

    // Set up ResizeObserver for better resize detection
    if (window.ResizeObserver) {
      resizeObserverRef.current = new ResizeObserver(entries => {
        // Use requestAnimationFrame to debounce resize calls
        requestAnimationFrame(() => {
          handleResize();
        });
      });
      resizeObserverRef.current.observe(chartContainerRef.current);
    }

    // Fallback to window resize event
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);

      // Cleanup event listeners
      if (chartContainerRef.current) {
        chartContainerRef.current.removeEventListener('wheel', handleChartInteraction);
        chartContainerRef.current.removeEventListener('mousedown', handleChartInteraction);
        chartContainerRef.current.removeEventListener('touchstart', handleChartInteraction);
      }

      // Cleanup ResizeObserver
      if (resizeObserverRef.current) {
        resizeObserverRef.current.disconnect();
      }

      if (chart) {
        chart.remove();
      }
    };
  }, [symbol, handleResize, handleChartInteraction]);

  // Add effect to handle chart resize when container dimensions change
  useEffect(() => {
    if (!chartReady) return;

    // Small delay to ensure DOM has updated
    const timeoutId = setTimeout(() => {
      handleResize();
    }, 50);

    return () => clearTimeout(timeoutId);
  }, [chartReady, handleResize]);

  // Update chart data when symbol or timeframe changes (non-replay mode)
  useEffect(() => {
    if (!chartReady || !symbol || !timeframe || isReplayMode) return;
    if (!chartReady || !symbol || !timeframe || isReplayMode) return;

    console.log('Fetching chart data for:', symbol, timeframe);
    fetchChartData();
  }, [chartReady, symbol, timeframe, isReplayMode]);

  // Handle replay mode initialization
  useEffect(() => {
    if (!chartReady || !isReplayMode) return;

    console.log('Initializing replay mode');
    // Reset auto-scroll and user interaction state when entering replay mode
    setAutoScroll(true);
    setUserInteracted(false);
    
    // Clear existing data when entering replay mode
    setReplayDataHistory([]);
    
    if (candlestickSeriesRef.current && volumeSeriesRef.current) {
      candlestickSeriesRef.current.setData([]);
      volumeSeriesRef.current.setData([]);
    }
  }, [chartReady, isReplayMode]);

  // Handle replay data updates
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
        updateChart(data.data);
      }
    } catch (error) {
      console.error('Error fetching chart data:', error);
    }
  };

  const updateChart = useCallback((data) => {
    if (!candlestickSeriesRef.current || !volumeSeriesRef.current) return;

    console.log('Updating chart with', data.length, 'bars');

    // Prepare candlestick data
    const candlestickData = data.map(bar => ({
      time: new Date(bar.time).getTime() / 1000,
      open: bar.open,
      high: bar.high,
      low: bar.low,
      close: bar.close,
    }));

    // Prepare volume data
    const volumeData = data.map(bar => ({
      time: new Date(bar.time).getTime() / 1000,
      value: bar.volume,
      color: bar.close >= bar.open ? 'rgba(38, 166, 154, 0.4)' : 'rgba(239, 83, 80, 0.4)',
    }));

    // Update series
    candlestickSeriesRef.current.setData(candlestickData);
    volumeSeriesRef.current.setData(volumeData);

    // Fit content with some padding
    // Fit content with some padding
    if (chartRef.current) {
      chartRef.current.timeScale().fitContent();
    }

    // Ensure chart is properly sized after data update
    setTimeout(handleResize, 100);
  }, [handleResize]);

    // Ensure chart is properly sized after data update
    setTimeout(handleResize, 100);
  }, [handleResize]);

  const updateChartWithReplayData = useCallback((barData) => {
    if (!candlestickSeriesRef.current || !volumeSeriesRef.current) return;

    console.log('Processing replay bar:', barData);

    const time = new Date(barData.timestamp).getTime() / 1000;

    // Add to history
    setReplayDataHistory(prev => {
      const newHistory = [...prev, barData];
      return newHistory;
    });

    // Create candlestick bar
    const candlestickBar = {
      time: time,
      open: barData.open,
      high: barData.high,
      low: barData.low,
      close: barData.close,
    };

    // Create volume bar
    const volumeBar = {
      time: time,
      value: barData.volume,
      color: barData.close >= barData.open ? 'rgba(38, 166, 154, 0.4)' : 'rgba(239, 83, 80, 0.4)',
    };

    try {
      // Update candlestick series
      candlestickSeriesRef.current.update(candlestickBar);
      
      // Update volume series
      volumeSeriesRef.current.update(volumeBar);

      // Only auto-scroll if user hasn't interacted with the chart
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

  // Function to manually enable/disable auto-scroll
  const toggleAutoScroll = () => {
    setAutoScroll(!autoScroll);
    setUserInteracted(!autoScroll); // If enabling auto-scroll, reset user interaction
  };

  // Function to scroll to latest data manually
  const scrollToLatest = () => {
    if (chartRef.current) {
      chartRef.current.timeScale().scrollToRealTime();
      setAutoScroll(true);
      setUserInteracted(false);
    }
  };

  return (
    <div className="trading-chart-maximized">
      {/* Compact Timeframe Selector */}
      <div className="timeframe-bar">
        <TimeframeDropdown
          timeframes={timeframes}
          timeframe={timeframe}
          handleTimeframeClick={handleTimeframeClick}
          isReplayMode={isReplayMode}
        />

        {/* Chart Info */}
        <div className="chart-info">
          {isReplayMode && (
            <>
              <span className="replay-indicator">
                🔄 REPLAY MODE
              </span>
              <span className="replay-bar-count">
                Bars: {replayDataHistory.length}
              </span>
              {/* Auto-scroll controls */}
              <button 
                className={`auto-scroll-btn ${autoScroll ? 'active' : ''}`}
                onClick={toggleAutoScroll}
                title={autoScroll ? 'Disable auto-scroll' : 'Enable auto-scroll'}
              >
                {autoScroll ? '🔒 Auto' : '🔓 Manual'}
              </button>
              {!autoScroll && (
                <button 
                  className="scroll-to-latest-btn"
                  onClick={scrollToLatest}
                  title="Scroll to latest data"
                >
                  ⏭️ Latest
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {/* Maximized Chart Container */}
      <div
        ref={chartContainerRef}
        className="chart-container-maximized"
      />

      {/* Minimal Footer with Attribution */}
      <div className="chart-footer">
        <div className="chart-attribution">
          <a
            href="https://www.tradingview.com"
            target="_blank"
            rel="noopener noreferrer"
          >
            Powered by TradingView
          </a>
        </div>
      </div>
    </div>
  );
};

export default TradingChart;