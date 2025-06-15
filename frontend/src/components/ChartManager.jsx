// ChartManager.js
export default class ChartManager {
    constructor({ chart, candleSeries, chartElement, onTrendlineComplete }) {
        this.chart = chart;
        this.candleseries = candleSeries;
        this.domElement = chartElement;

        this.onTrendlineComplete = onTrendlineComplete;

        this.xspan = null;
        this.klines = null;
        this.startPoint = null;
        this.isUpdatingLine = false;
        this.isHovered = false;
        this.isDragging = false;
        this.dragStartPoint = null;
        this.dragStartLineData = null;
        this.lastCrosshairPosition = null;
        this.selectedPoint = null;
        this.hoverThreshold = 2; // Increased threshold for easier selection
        this.activeLine = null;
        this.tempLine = null; // For drawing preview
        this.trendlineMode = false;

        this.subscribeToEvents();
    }

    subscribeToEvents() {
        this.chart.subscribeClick(this.handleChartClick.bind(this));
        this.chart.subscribeCrosshairMove(this.handleCrosshairMove.bind(this));
        this.domElement.addEventListener('mousedown', this.handleMouseDown.bind(this));
        this.domElement.addEventListener('mouseup', this.handleMouseUp.bind(this));
    }

    setData(data) {
        this.klines = data;
        this.xspan = data.map(d => d.time).map((d, i, arr) => (i ? arr[i] - arr[i - 1] : 0))[2];
    }

    handleChartClick(param) {
        if (!this.trendlineMode || this.isUpdatingLine || this.isDragging) return;

        const xTs = param.time ?? (this.klines?.[0]?.time + param.logical * this.xspan);
        const yPrice = this.candleseries.coordinateToPrice(param.point.y);

        if (!this.startPoint) {
            // First click - set start point and create temp line
            this.startPoint = { time: xTs, price: yPrice };
            this.tempLine = this.chart.addLineSeries({
                color: 'rgba(54, 162, 235, 0.8)',
                lineWidth: 2,
                lineStyle: 1, // Dashed line for preview
            });
        } else {
            // Second click - finalize the line
            if (this.tempLine) {
                this.chart.removeSeries(this.tempLine);
                this.tempLine = null;
            }

            // Create the final trendline
            this.activeLine = this.chart.addLineSeries({
                color: 'dodgerblue',
                lineWidth: 2,
                lineStyle: 0, // Solid line
            });

            const lineData = [
                { time: this.startPoint.time, value: this.startPoint.price },
                { time: xTs, value: yPrice }
            ];

            this.activeLine.setData(lineData);

            // Reset state
            this.startPoint = null;
            this.selectedPoint = null;
            this.trendlineMode = false;
            if (this.onTrendlineComplete) this.onTrendlineComplete();
        }
    }

    handleCrosshairMove(param) {
        if (this.isUpdatingLine || !param.point) return;
        
        const xTs = param.time ?? (this.klines?.[0]?.time + param.logical * this.xspan);
        const yPrice = this.candleseries.coordinateToPrice(param.point.y);
        
        // Validate the calculated values
        if (!this.isValidTime(xTs) || !this.isValidPrice(yPrice)) {
            return;
        }
        
        this.lastCrosshairPosition = { x: xTs, y: yPrice };

        if (this.trendlineMode && this.startPoint && this.tempLine) {
            // Update temp line preview
            this.updateTempLine(xTs, yPrice);
        } else if (!this.trendlineMode) {
            // Handle hover effect for existing lines
            this.handleHoverEffect(xTs, yPrice);
        }

        if (this.isDragging && this.activeLine) {
            const deltaX = xTs - this.dragStartPoint.x;
            const deltaY = yPrice - this.dragStartPoint.y;

            const newLineData = this.dragStartLineData.map((point, i) => {
                const newTime = point.time + (this.selectedPoint !== null && i === this.selectedPoint ? deltaX : 
                                this.selectedPoint === null ? deltaX : 0);
                const newValue = point.value + (this.selectedPoint !== null && i === this.selectedPoint ? deltaY : 
                                this.selectedPoint === null ? deltaY : 0);
                
                return {
                    time: this.clampTime(newTime),
                    value: this.clampPrice(newValue)
                };
            });

            // Ensure time ordering is maintained
            if (this.isValidLineData(newLineData)) {
                this.dragLine(newLineData);
            }
        }
    }

    setTrendlineMode(enabled) {
        this.trendlineMode = enabled;
        if (!enabled) {
            // Clean up temp line if mode is disabled
            if (this.tempLine) {
                this.chart.removeSeries(this.tempLine);
                this.tempLine = null;
            }
            this.startPoint = null;
        }
    }

    handleMouseDown() {
        if (!this.lastCrosshairPosition || !this.isHovered || this.trendlineMode) return;
        this.startDrag(this.lastCrosshairPosition.x, this.lastCrosshairPosition.y);
    }

    handleMouseUp() {
        this.endDrag();
    }

    updateTempLine(xTs, yPrice) {
        if (!this.tempLine || !this.startPoint) return;
        
        // Validate inputs
        if (!this.isValidTime(xTs) || !this.isValidPrice(yPrice)) return;
        
        // Allow drawing in both directions - remove the restrictive time check
        const startTime = this.startPoint.time;
        const endTime = xTs;
        
        // Create line data with proper time ordering
        const lineData = startTime <= endTime 
            ? [
                { time: startTime, value: this.startPoint.price },
                { time: endTime, value: yPrice }
              ]
            : [
                { time: endTime, value: yPrice },
                { time: startTime, value: this.startPoint.price }
              ];
        
        if (!this.isValidLineData(lineData)) return;
        
        try {
            this.isUpdatingLine = true;
            this.tempLine.setData(lineData);
        } catch (error) {
            console.error('Error updating temp line:', error);
        } finally {
            this.isUpdatingLine = false;
        }
    }

    handleHoverEffect(xTs, yPrice) {
        if (!this.activeLine) return;
        
        const linedata = this.activeLine.data();
        if (!linedata || linedata.length < 2) return;

        const hovered = this.isLineHovered(xTs, yPrice, linedata[0], linedata[1]);
        
        if (hovered && !this.isHovered) {
            this.startHover();
        } else if (!hovered && this.isHovered && !this.isDragging) {
            this.endHover();
        }
    }

    startHover() {
        this.isHovered = true;
        this.domElement.style.cursor = "pointer";
        this.chart.applyOptions({ handleScroll: false, handleScale: false });
        
        if (this.activeLine) {
            this.activeLine.applyOptions({ 
                color: 'orange', 
                lineWidth: 3 
            });
        }
    }

    endHover() {
        this.isHovered = false;
        this.domElement.style.cursor = "default";
        this.chart.applyOptions({ handleScroll: true, handleScale: true });
        
        if (this.activeLine) {
            this.activeLine.applyOptions({ 
                color: 'dodgerblue', 
                lineWidth: 2 
            });
        }
    }

    startDrag(xTs, yPrice) {
        if (!this.activeLine) return;
        
        this.isDragging = true;
        this.dragStartPoint = { x: xTs, y: yPrice };
        this.dragStartLineData = [...this.activeLine.data()];
    }

    endDrag() {
        this.isDragging = false;
        this.dragStartPoint = null;
        this.dragStartLineData = null;
        this.selectedPoint = null;
    }

    dragLine(newCords) {
        if (!this.activeLine) return;
        
        // Additional validation before updating
        if (!this.isValidLineData(newCords)) {
            console.warn('Invalid line data, skipping update:', newCords);
            return;
        }
        
        try {
            this.isUpdatingLine = true;
            this.activeLine.setData(newCords);
        } catch (error) {
            console.error('Error updating line data:', error);
            // Revert to original data if update fails
            if (this.dragStartLineData && this.isValidLineData(this.dragStartLineData)) {
                try {
                    this.activeLine.setData(this.dragStartLineData);
                } catch (revertError) {
                    console.error('Failed to revert line data:', revertError);
                }
            }
        } finally {
            this.isUpdatingLine = false;
        }
    }

    deleteSelectedLine() {
        if (this.activeLine && this.isHovered && !this.isDragging) {
            console.log("Deleting trendline:", this.activeLine.data());

            this.chart.removeSeries(this.activeLine);
            this.activeLine = null;
            this.startPoint = null;
            this.selectedPoint = null;
            this.isHovered = false;
            this.endHover(); // Reset cursor and chart options

            setTimeout(() => {
                this.chart.timeScale().fitContent();
            }, 50);

            return true; // Indicate successful deletion
        }
        return false;
    }

    isLineHovered(xTs, yPrice, point1, point2) {
        if (this.isDragging) return true;
        if (!point1 || !point2) return false;

        // Check if hovering near endpoints
        const isNearEndpoint = (pt, index) => {
            const timeDiff = Math.abs(xTs - pt.time);
            const priceDiff = Math.abs(yPrice - pt.value);
            const priceThreshold = (pt.value * this.hoverThreshold) / 100;
            
            // More lenient threshold for time (allow some pixels of tolerance)
            const timeThreshold = this.xspan * 5; // 5 bars worth of time
            
            if (timeDiff <= timeThreshold && priceDiff <= priceThreshold) {
                this.selectedPoint = index;
                return true;
            }
            return false;
        };

        if (isNearEndpoint(point1, 0) || isNearEndpoint(point2, 1)) {
            return true;
        }

        // Check if hovering near the line itself
        this.selectedPoint = null;
        
        // Only check line intersection if cursor is within the time range of the line
        const minTime = Math.min(point1.time, point2.time);
        const maxTime = Math.max(point1.time, point2.time);
        
        if (xTs >= minTime && xTs <= maxTime) {
            const slope = (point2.value - point1.value) / (point2.time - point1.time);
            const estimatedY = point1.value + slope * (xTs - point1.time);
            const priceDiff = Math.abs(yPrice - estimatedY);
            const priceThreshold = (estimatedY * this.hoverThreshold) / 100;
            
            return priceDiff <= priceThreshold;
        }
        
        return false;
    }

    // Method to get all active trendlines (for future multi-line support)
    getActiveTrendlines() {
        return this.activeLine ? [this.activeLine] : [];
    }

    // Method to clear all trendlines
    clearAllTrendlines() {
        if (this.activeLine) {
            this.chart.removeSeries(this.activeLine);
            this.activeLine = null;
        }
        if (this.tempLine) {
            this.chart.removeSeries(this.tempLine);
            this.tempLine = null;
        }
        this.startPoint = null;
        this.selectedPoint = null;
        this.isHovered = false;
        this.isDragging = false;
        this.endHover();
    }

    // Validation and clamping methods
    isValidTime(time) {
        return typeof time === 'number' && !isNaN(time) && isFinite(time) && time > 0;
    }

    isValidPrice(price) {
        return typeof price === 'number' && !isNaN(price) && isFinite(price) && price > 0;
    }

    clampTime(time) {
        if (!this.isValidTime(time)) {
            return this.klines?.[0]?.time || Date.now() / 1000;
        }
        
        // Remove restrictive time clamping to allow extending beyond visible range
        return time;
    }

    clampPrice(price) {
        if (!this.isValidPrice(price)) {
            return 1; // Default fallback price
        }
        
        // Get price scale bounds
        const priceScale = this.candleseries.priceScale();
        if (priceScale) {
            try {
                const visibleRange = priceScale.getVisibleRange();
                if (visibleRange) {
                    const minPrice = visibleRange.from;
                    const maxPrice = visibleRange.to;
                    const buffer = (maxPrice - minPrice) * 0.5; // Increased buffer for prices
                    
                    return Math.max(minPrice - buffer, Math.min(maxPrice + buffer, price));
                }
            } catch (e) {
                // Fallback if getVisibleRange is not available
            }
        }
        
        // Ensure price is positive and reasonable
        return Math.max(0.0001, price);
    }

    isValidLineData(lineData) {
        if (!lineData || lineData.length < 2) return false;
        
        for (let i = 0; i < lineData.length; i++) {
            const point = lineData[i];
            if (!this.isValidTime(point.time) || !this.isValidPrice(point.value)) {
                return false;
            }
        }
        
        // Ensure time ordering for the line data
        for (let i = 1; i < lineData.length; i++) {
            if (lineData[i].time <= lineData[i - 1].time) {
                return false;
            }
        }
        
        return true;
    }
}