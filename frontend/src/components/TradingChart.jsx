// frontend/src/components/TradingChart.js

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { createChart, ColorType } from 'lightweight-charts';
import './TradingChart.css'; // Import your CSS styles

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
  const [chartReady, setChartReady] = useState(false);

  // Available timeframes
  const timeframes = [
    { value: '1h', label: '1H' },
    { value: '4h', label: '4H' },
    { value: '1d', label: '1D' },
    { value: '1w', label: '1W' },
    { value: '1m', label: '1M' }
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

  // Initialize chart
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
        bottom: 0,
      },
      textColor: '#888',
    });

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
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      
      // Cleanup ResizeObserver
      if (resizeObserverRef.current) {
        resizeObserverRef.current.disconnect();
      }
      
      if (chart) {
        chart.remove();
      }
    };
  }, [symbol, handleResize]);

  // Add effect to handle chart resize when container dimensions change
  useEffect(() => {
    if (!chartReady) return;
    
    // Small delay to ensure DOM has updated
    const timeoutId = setTimeout(() => {
      handleResize();
    }, 50);

    return () => clearTimeout(timeoutId);
  }, [chartReady, handleResize]);

  // Update chart data when symbol or timeframe changes
  useEffect(() => {
    if (!chartReady || !symbol || !timeframe || isReplayMode) return;

    fetchChartData();
  }, [chartReady, symbol, timeframe, isReplayMode]);

  // Handle replay data updates
  useEffect(() => {
    if (!chartReady || !isReplayMode || !replayData) return;

    updateChartWithReplayData(replayData);
  }, [chartReady, isReplayMode, replayData]);

  const fetchChartData = async () => {
    try {
      const response = await fetch(`http://localhost:8000/commodities/${symbol}?timeframe=${timeframe}`);
      const data = await response.json();

      if (data && data.data) {
        updateChart(data.data);
      }
    } catch (error) {
      console.error('Error fetching chart data:', error);
    }
  };

  const updateChart = useCallback((data) => {
    if (!candlestickSeriesRef.current || !volumeSeriesRef.current) return;

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
    if (chartRef.current) {
      chartRef.current.timeScale().fitContent();
    }

    // Ensure chart is properly sized after data update
    setTimeout(handleResize, 100);
  }, [handleResize]);

  const updateChartWithReplayData = useCallback((barData) => {
    if (!candlestickSeriesRef.current || !volumeSeriesRef.current) return;

    const time = new Date(barData.timestamp).getTime() / 1000;
    
    // Update candlestick
    candlestickSeriesRef.current.update({
      time: time,
      open: barData.open,
      high: barData.high,
      low: barData.low,
      close: barData.close,
    });

    // Update volume
    volumeSeriesRef.current.update({
      time: time,
      value: barData.volume,
      color: barData.close >= barData.open ? 'rgba(38, 166, 154, 0.4)' : 'rgba(239, 83, 80, 0.4)',
    });

    // Auto-scroll to latest data
    if (chartRef.current) {
      chartRef.current.timeScale().scrollToRealTime();
    }
  }, []);

  const handleTimeframeClick = (newTimeframe) => {
    if (newTimeframe !== timeframe && onTimeframeChange) {
      onTimeframeChange(newTimeframe);
    }
  };

  return (
    <div className="trading-chart-maximized">
      {/* Compact Timeframe Selector */}
      <div className="timeframe-bar">
        <div className="timeframe-selector-compact">
          {timeframes.map((tf) => (
            <button
              key={tf.value}
              className={`timeframe-btn-compact ${timeframe === tf.value ? 'active' : ''}`}
              onClick={() => handleTimeframeClick(tf.value)}
              disabled={isReplayMode}
            >
              {tf.label}
            </button>
          ))}
        </div>
        
        {/* Chart Info */}
        <div className="chart-info">
          {/* <span className="chart-symbol">{symbol}</span>
          <span className="chart-timeframe">{timeframe}</span> */}
          {isReplayMode && (
            <span className="replay-indicator">
              🔄 REPLAY MODE
            </span>
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