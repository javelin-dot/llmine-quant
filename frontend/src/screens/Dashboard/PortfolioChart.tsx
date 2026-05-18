import { useEffect, useMemo, useRef, useState } from 'react'
import * as echarts from 'echarts'
import { useDashboard } from '../../contexts/DashboardContext'

type TimeRange = '1M' | '3M' | '6M' | '1Y' | 'ALL'

const RANGE_WEEKS: Record<TimeRange, number> = {
  '1M': 4,
  '3M': 12,
  '6M': 24,
  '1Y': 52,
  ALL: 999,
}

function formatPercent(v: number): string {
  const sign = v >= 0 ? '+' : ''
  return `${sign}${(v * 100).toFixed(2)}%`
}

export default function PortfolioChart() {
  const data = useDashboard()
  const containerRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<echarts.ECharts | null>(null)
  const [range, setRange] = useState<TimeRange>('6M')

  const series = useMemo(() => {
    const all = data.equityCurve
    const weeks = RANGE_WEEKS[range]
    return weeks >= all.length ? all : all.slice(all.length - weeks)
  }, [range])

  const metrics = data.portfolioMetrics

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const chart = echarts.init(el, undefined, { renderer: 'canvas' })
    chartRef.current = chart

    const ro = new ResizeObserver(() => chart.resize())
    ro.observe(el)

    const onResize = () => chart.resize()
    window.addEventListener('resize', onResize)
    return () => {
      ro.disconnect()
      window.removeEventListener('resize', onResize)
      chart.dispose()
      chartRef.current = null
    }
  }, [])

  useEffect(() => {
    const chart = chartRef.current
    if (!chart) return

    const dates = series.map((p) => p.date)
    const values = series.map((p) => +(p.value * 100 - 100).toFixed(2))
    const benchmark = series.map((p) => +(p.benchmark * 100 - 100).toFixed(2))

    chart.setOption({
      grid: { left: 8, right: 16, top: 28, bottom: 30, containLabel: true },
      animationDuration: 800,
      animationEasing: 'cubicOut',
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(15, 21, 43, 0.94)',
        borderColor: 'rgba(76, 141, 255, 0.4)',
        borderWidth: 1,
        textStyle: { color: '#eef4ff', fontSize: 12 },
        axisPointer: {
          type: 'cross',
          lineStyle: { color: 'rgba(66, 232, 255, 0.4)', type: 'dashed' },
        },
        valueFormatter: (v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`,
      },
      legend: {
        data: ['组合净值', metrics.benchmark],
        top: 0,
        right: 8,
        textStyle: { color: '#8f9bb7', fontSize: 11 },
        itemWidth: 10,
        itemHeight: 10,
      },
      xAxis: {
        type: 'category',
        data: dates,
        boundaryGap: false,
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
        axisLabel: {
          color: '#5f6b85',
          fontSize: 10,
          formatter: (val: string) => {
            const [, m, d] = val.split('-')
            return `${m}/${d}`
          },
        },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'value',
        axisLine: { show: false },
        axisLabel: {
          color: '#5f6b85',
          fontSize: 10,
          formatter: (v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(0)}%`,
        },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
      },
      series: [
        {
          name: '组合净值',
          type: 'line',
          smooth: true,
          symbol: 'none',
          lineStyle: {
            width: 2.5,
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: '#4c8dff' },
              { offset: 0.5, color: '#42e8ff' },
              { offset: 1, color: '#4ff0a2' },
            ]),
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(66, 232, 255, 0.32)' },
              { offset: 1, color: 'rgba(66, 232, 255, 0)' },
            ]),
          },
          emphasis: { focus: 'series' },
          data: values,
        },
        {
          name: metrics.benchmark,
          type: 'line',
          smooth: true,
          symbol: 'none',
          lineStyle: {
            width: 1.5,
            color: 'rgba(143, 155, 183, 0.7)',
            type: 'dashed',
          },
          data: benchmark,
        },
      ],
    })
  }, [series, metrics.benchmark])

  return (
    <div className="portfolio-chart">
      <div className="portfolio-chart-head">
        <div>
          <h3 className="portfolio-chart-title">Portfolio Performance</h3>
          <span className="portfolio-chart-sub">AI 管理 · 模拟盘 + 实盘</span>
        </div>
        <div className="portfolio-chart-ranges">
          {(['1M', '3M', '6M', '1Y', 'ALL'] as TimeRange[]).map((r) => (
            <button
              key={r}
              className={r === range ? 'range-btn active' : 'range-btn'}
              onClick={() => setRange(r)}
            >
              {r}
            </button>
          ))}
        </div>
      </div>
      <div className="portfolio-chart-canvas" ref={containerRef} />
      <div className="portfolio-chart-metrics">
        <div className="metric-pill">
          <span className="metric-label">累计收益</span>
          <span className={`metric-value ${metrics.totalReturn >= 0 ? 'pos' : 'neg'}`}>
            {formatPercent(metrics.totalReturn)}
          </span>
        </div>
        <div className="metric-pill">
          <span className="metric-label">年化收益</span>
          <span className={`metric-value ${metrics.annualReturn >= 0 ? 'pos' : 'neg'}`}>
            {formatPercent(metrics.annualReturn)}
          </span>
        </div>
        <div className="metric-pill">
          <span className="metric-label">最大回撤</span>
          <span className="metric-value neg">{formatPercent(metrics.maxDrawdown)}</span>
        </div>
        <div className="metric-pill">
          <span className="metric-label">夏普比率</span>
          <span className="metric-value">{metrics.sharpeRatio.toFixed(2)}</span>
        </div>
        <div className="metric-pill">
          <span className="metric-label">索提诺比率</span>
          <span className="metric-value">{metrics.sortinoRatio.toFixed(2)}</span>
        </div>
        <div className="metric-pill subtle">
          <span className="metric-label">基准 ({metrics.benchmark})</span>
          <span className={`metric-value ${metrics.benchmarkReturn >= 0 ? 'pos' : 'neg'}`}>
            {formatPercent(metrics.benchmarkReturn)}
          </span>
        </div>
      </div>
    </div>
  )
}
