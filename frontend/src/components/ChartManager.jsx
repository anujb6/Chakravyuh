// ChartManager.js
export default class ChartManager {
    constructor({ chart, candleSeries, chartElement, onTrendlineComplete }) {
        this.chart = chart;
        this.candleseries = candleSeries;
        this.domElement = chartElement;

        this.lineSeries = this.chart.addLineSeries();
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
        this.hoverThreshold = 0.01;
        this.activeLine = null;

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
            this.startPoint = { time: xTs, price: yPrice };
        } else {
            this.activeLine = this.chart.addLineSeries();
            this.activeLine.setData([
                { time: this.startPoint.time, value: this.startPoint.price },
                { time: xTs, value: yPrice }
            ]);

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
        this.lastCrosshairPosition = { x: xTs, y: yPrice };

        if (this.trendlineMode && this.startPoint) {
            this.updateLine(xTs, yPrice);
        } else {
            this.handleHoverEffect(xTs, yPrice);
        }

        if (this.isDragging) {
            const deltaX = xTs - this.dragStartPoint.x;
            const deltaY = yPrice - this.dragStartPoint.y;

            const newLineData = this.dragStartLineData.map((point, i) =>
                this.selectedPoint !== null && i === this.selectedPoint
                    ? { time: point.time + deltaX, value: point.value + deltaY }
                    : this.selectedPoint !== null
                        ? point
                        : { time: point.time + deltaX, value: point.value + deltaY }
            );

            this.dragLine(newLineData);
        }
    }
    setTrendlineMode(enabled) {
        this.trendlineMode = enabled;
    }

    handleMouseDown() {
        if (!this.lastCrosshairPosition || !this.isHovered) return;
        this.startDrag(this.lastCrosshairPosition.x, this.lastCrosshairPosition.y);
    }

    handleMouseUp() {
        this.endDrag();
    }

    handleLineDrawing(xTs, yPrice) {
        if (!this.startPoint) {
            this.startPoint = { time: xTs, price: yPrice };
        } else {
            this.lineSeries.setData([
                { time: this.startPoint.time, value: this.startPoint.price },
                { time: xTs, value: yPrice }
            ]);
            this.startPoint = null;
            this.selectedPoint = null;
        }
        this.trendlineMode = false;
        if (this.onTrendlineComplete) this.onTrendlineComplete();
    }

    handleHoverEffect(xTs, yPrice) {
        if (!this.activeLine) return;
        const linedata = this.activeLine.data();
        if (!linedata.length) return;

        const hovered = this.isLineHovered(xTs, yPrice, linedata[0], linedata[1]);
        if (hovered && !this.isHovered) this.startHover();
        if (!hovered && this.isHovered && !this.isDragging) this.endHover();
    }

    startHover() {
        this.isHovered = true;
        this.lineSeries.applyOptions({ color: "orange" });
        this.domElement.style.cursor = "pointer";
        this.chart.applyOptions({ handleScroll: false, handleScale: false });
        this.activeLine.applyOptions({ color: 'red', lineWidth: 3 });
    }

    endHover() {
        this.isHovered = false;
        this.lineSeries.applyOptions({ color: "dodgerblue" });
        this.domElement.style.cursor = "default";
        this.chart.applyOptions({ handleScroll: true, handleScale: true });
        this.activeLine.applyOptions({ color: 'dodgerblue', lineWidth: 1 });
    }

    startDrag(xTs, yPrice) {
        this.isDragging = true;
        this.dragStartPoint = { x: xTs, y: yPrice };
        this.dragStartLineData = [...this.lineSeries.data()];
    }

    endDrag() {
        this.isDragging = false;
        this.dragStartPoint = null;
        this.dragStartLineData = null;
        this.selectedPoint = null;
    }

    updateLine(xTs, yPrice) {
        this.isUpdatingLine = true;
        this.lineSeries.setData([
            { time: this.startPoint.time, value: this.startPoint.price },
            { time: xTs, value: yPrice }
        ]);
        this.selectedPoint = null;
        this.isUpdatingLine = false;
    }

    dragLine(newCords) {
        this.isUpdatingLine = true;
        this.lineSeries.setData(newCords);
        this.isUpdatingLine = false;
    }

    deleteSelectedLine() {
        if (this.activeLine && this.isHovered && !this.isDragging) {
            console.log("Attempting to delete:", this.activeLine.data());

            this.chart.removeSeries(this.activeLine);
            this.activeLine = null;
            this.startPoint = null;
            this.selectedPoint = null;
            this.isHovered = false;

            setTimeout(() => {
                this.chart.timeScale().fitContent();
            }, 50);
        }
    }

    isLineHovered(xTs, yPrice, point1, point2) {
        if (this.isDragging) return true;

        const isNear = (pt, index) => {
            const isCloseX = xTs === pt.time;
            const isCloseY = (Math.abs(yPrice - pt.value) * 100) / yPrice < this.hoverThreshold;
            if (isCloseX && isCloseY) {
                this.selectedPoint = index;
                return true;
            }
            return false;
        };

        if (isNear(point1, 0) || isNear(point2, 1)) return true;

        this.selectedPoint = null;
        const m = (point2.value - point1.value) / (point2.time - point1.time);
        const estimatedY = m * xTs + (point1.value - m * point1.time);
        return (Math.abs(yPrice - estimatedY) * 100) / yPrice < this.hoverThreshold;
    }
}
