// frontend/src/components/TradingChart.js

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { createChart, ColorType } from 'lightweight-charts';

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
  const [chartReady, setChartReady] = useState(false);

  // Available timeframes
  const timeframes = [
    { value: '1h', label: '1H' },
    { value: '2h', label: '2H' },
    { value: '4h', label: '4H' },
    { value: '1d', label: '1D' },
    { value: '1w', label: '1W' },
    { value: '1m', label: '1M' }
  ];

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#1e1e1e' },
        textColor: '#d1d4dc',
      },
      grid: {
        vertLines: { color: '#2B2B43' },
        horzLines: { color: '#2B2B43' },
      },
      crosshair: {
        mode: 1,
      },
      rightPriceScale: {
        borderColor: '#2B2B43',
      },
      timeScale: {
        borderColor: '#2B2B43',
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
        top: 0.8,
        bottom: 0,
      },
    });

    chartRef.current = chart;
    candlestickSeriesRef.current = candlestickSeries;
    volumeSeriesRef.current = volumeSeries;
    setChartReady(true);

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [symbol]);

  // Update chart data when symbol or timeframe changes
  useEffect(() => {
    if (!chartReady || !symbol || !timeframe) return;

    fetchChartData();
  }, [chartReady, symbol, timeframe]);

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
      color: bar.close >= bar.open ? 'rgba(38, 166, 154, 0.5)' : 'rgba(239, 83, 80, 0.5)',
    }));

    // Update series
    candlestickSeriesRef.current.setData(candlestickData);
    volumeSeriesRef.current.setData(volumeData);

    // Fit content
    if (chartRef.current) {
      chartRef.current.timeScale().fitContent();
    }
  }, []);

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
      color: barData.close >= barData.open ? 'rgba(38, 166, 154, 0.5)' : 'rgba(239, 83, 80, 0.5)',
    });
  }, []);

  const handleTimeframeClick = (newTimeframe) => {
    if (newTimeframe !== timeframe && onTimeframeChange) {
      onTimeframeChange(newTimeframe);
    }
  };

  return (
    <div className="trading-chart-container">
      {/* Timeframe Selection */}
      <div className="timeframe-selector">
        {timeframes.map((tf) => (
          <button
            key={tf.value}
            className={`timeframe-btn ${timeframe === tf.value ? 'active' : ''}`}
            onClick={() => handleTimeframeClick(tf.value)}
            disabled={isReplayMode}
          >
            {tf.label}
          </button>
        ))}
      </div>

      {/* Chart Container */}
      <div 
        ref={chartContainerRef} 
        className="chart-container"
        style={{ width: '100%', height: '600px' }}
      />

      {/* TradingView Attribution */}
      <div className="tradingview-attribution">
        <a 
          href="https://www.tradingview.com" 
          target="_blank" 
          rel="noopener noreferrer"
          style={{ color: '#666', fontSize: '12px', textDecoration: 'none' }}
        >
          Powered by TradingView
        </a>
      </div>
    </div>
  );
};

export default TradingChart;