
import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, CandlestickSeries, LineSeries } from 'lightweight-charts';

const TradingViewChart = ({ data, type = 'candlestick', colors = {} }) => {
    const chartContainerRef = useRef();

    useEffect(() => {
        if (!data || data.length === 0) return;

        const chartOptions = {
            layout: {
                background: { type: ColorType.Solid, color: 'transparent' },
                textColor: '#94a3b8',
            },
            grid: {
                vertLines: { color: 'rgba(51, 65, 85, 0.2)' },
                horzLines: { color: 'rgba(51, 65, 85, 0.2)' },
            },
            width: chartContainerRef.current.clientWidth,
            height: 300,
        };

        const chart = createChart(chartContainerRef.current, chartOptions);

        // Sort data by time just in case
        const sortedData = [...data].sort((a, b) => new Date(a.time) - new Date(b.time));

        let series;
        if (type === 'candlestick') {
            // v5 API: use addSeries with CandlestickSeries
            series = chart.addSeries(CandlestickSeries, {
                upColor: '#22c55e',
                downColor: '#ef4444',
                borderVisible: false,
                wickUpColor: '#22c55e',
                wickDownColor: '#ef4444',
            });
        } else {
            // v5 API: use addSeries with LineSeries
            series = chart.addSeries(LineSeries, {
                color: '#3b82f6',
                lineWidth: 2,
            });
        }

        series.setData(sortedData);
        chart.timeScale().fitContent();

        // SIMULATION: Real-time ticking effect
        let intervalId;
        if (type === 'candlestick' && sortedData.length > 0) {
            let lastCandle = { ...sortedData[sortedData.length - 1] };

            intervalId = setInterval(() => {
                const move = (Math.random() - 0.5) * (lastCandle.close * 0.002); // 0.2% variance
                const newPrice = lastCandle.close + move;

                // Update candle
                if (newPrice > lastCandle.high) lastCandle.high = newPrice;
                if (newPrice < lastCandle.low) lastCandle.low = newPrice;
                lastCandle.close = newPrice;

                series.update(lastCandle);
            }, 1000);
        }

        const handleResize = () => {
            if (chartContainerRef.current) {
                chart.applyOptions({ width: chartContainerRef.current.clientWidth });
            }
        };

        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            if (intervalId) clearInterval(intervalId);
            chart.remove();
        };
    }, [data, type]);

    return <div ref={chartContainerRef} className="w-full h-[300px]" />;
};

export default TradingViewChart;
