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
  replayStartDate = null
}) => {
  const chartContainerRef = useRef();
  const chartRef = useRef();
  const candlestickSeriesRef = useRef();
  const volumeSeriesRef = useRef();
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

    chart.timeScale().subscribeVisibleTimeRangeChange(handleChartInteraction);
    chart.subscribeCrosshairMove(handleChartInteraction);
    
    if (chartContainerRef.current) {
      chartContainerRef.current.addEventListener('wheel', handleChartInteraction);
      chartContainerRef.current.addEventListener('mousedown', handleChartInteraction);
      chartContainerRef.current.addEventListener('touchstart', handleChartInteraction);
    }

    chartRef.current = chart;
    candlestickSeriesRef.current = candlestickSeries;
    volumeSeriesRef.current = volumeSeries;
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
  }, [symbol, handleResize, handleChartInteraction]);

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
    if (!candlestickSeriesRef.current || !volumeSeriesRef.current || !data.length) return;

    const candlestickData = data.map(bar => ({
      time: new Date(bar.time).getTime() / 1000,
      open: bar.open,
      high: bar.high,
      low: bar.low,
      close: bar.close,
    }));

    const volumeData = data.map(bar => ({
      time: new Date(bar.time).getTime() / 1000,
      value: bar.volume,
      color: bar.close >= bar.open ? 'rgba(38, 166, 154, 0.4)' : 'rgba(239, 83, 80, 0.4)',
    }));

    candlestickSeriesRef.current.setData(candlestickData);
    volumeSeriesRef.current.setData(volumeData);

    if (chartRef.current) {
      chartRef.current.timeScale().fitContent();
    }

    setTimeout(handleResize, 100);
  }, [handleResize]);

  const updateChartWithReplayData = useCallback((barData) => {
    if (!candlestickSeriesRef.current || !volumeSeriesRef.current) return;

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

    const volumeBar = {
      time: time,
      value: barData.volume,
      color: barData.close >= barData.open ? 'rgba(38, 166, 154, 0.4)' : 'rgba(239, 83, 80, 0.4)',
    };

    try {
      candlestickSeriesRef.current.update(candlestickBar);
      volumeSeriesRef.current.update(volumeBar);

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

  const toggleAutoScroll = () => {
    setAutoScroll(!autoScroll);
    setUserInteracted(!autoScroll);
  };

  const scrollToLatest = () => {
    if (chartRef.current) {
      chartRef.current.timeScale().scrollToRealTime();
      setAutoScroll(true);
      setUserInteracted(false);
    }
  };

  const getHistoricalBarsCount = () => {
    if (!isReplayMode || !replayStartTime || !historicalData.length) return 0;
    
    return historicalData.filter(bar => {
      const barTime = new Date(bar.time).getTime();
      return barTime < replayStartTime;
    }).length;
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
      </div>

      {/* Chart Container */}
      <div
        ref={chartContainerRef}
        className="chart-container-maximized"
      />

      {/* Footer with Attribution */}
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