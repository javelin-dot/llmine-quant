import { useEffect, useMemo, useRef } from 'react'
import * as echarts from 'echarts'
import type { BacktestEquityPointPayload } from '../../lib/api'

interface EquityChartProps {
  equity: BacktestEquityPointPayload[]
  inSampleEndDate: string | null
}

export default function EquityChart({ equity, inSampleEndDate }: EquityChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<echarts.ECharts | null>(null)

  const { dates, navValues, ddValues, splitIndex } = useMemo(() => {
    if (!equity.length) {
      return { dates: [], navValues: [], ddValues: [], splitIndex: -1 }
    }
    const base = equity[0].value || 1
    const dates = equity.map((p) => p.tradeDate)
    const navValues = equity.map((p) => +((p.value / base - 1) * 100).toFixed(3))
    const ddValues = equity.map((p) => +(((p.drawdown ?? 0)) * 100).toFixed(3))
    const splitIndex = inSampleEndDate
      ? equity.findIndex((p) => p.tradeDate > inSampleEndDate)
      : -1
    return { dates, navValues, ddValues, splitIndex }
  }, [equity, inSampleEndDate])

  useEffect(() => {
    if (!containerRef.current) return
    const el = containerRef.current

    const init = () => {
      if (!chartRef.current) {
        const rect = el.getBoundingClientRect()
        if (rect.width > 0 && rect.height > 0) {
          chartRef.current = echarts.init(el, undefined, { renderer: 'canvas' })
        }
      } else {
        chartRef.current.resize()
      }
    }
    init()
    const ro = new ResizeObserver(init)
    ro.observe(el)
    return () => {
      ro.disconnect()
      chartRef.current?.dispose()
      chartRef.current = null
    }
  }, [])

  useEffect(() => {
    if (!chartRef.current || dates.length === 0) return
    const markAreas =
      splitIndex > 0
        ? [
            [
              { xAxis: dates[splitIndex], itemStyle: { color: 'rgba(255, 159, 67, 0.06)' } },
              { xAxis: dates[dates.length - 1] },
            ],
          ]
        : []
    const markLines =
      splitIndex > 0
        ? [
            {
              xAxis: dates[splitIndex - 1] ?? dates[splitIndex],
              lineStyle: { color: '#ff9f43', type: 'dashed' as const, width: 1.4 },
              label: { formatter: 'IS / OOS', color: '#ff9f43', fontSize: 11 },
            },
          ]
        : []

    chartRef.current.setOption(
      {
        animationDuration: 600,
        tooltip: {
          trigger: 'axis',
          backgroundColor: 'rgba(15, 21, 43, 0.94)',
          borderColor: 'rgba(76, 141, 255, 0.4)',
          borderWidth: 1,
          textStyle: { color: '#eef4ff', fontSize: 12 },
          axisPointer: { type: 'cross', lineStyle: { color: 'rgba(66,232,255,.4)', type: 'dashed' } },
          valueFormatter: (v: number | null) => (v == null ? '—' : `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`),
        },
        legend: {
          data: ['Equity (累计收益)', 'Drawdown'],
          top: 0,
          right: 8,
          textStyle: { color: '#8f9bb7', fontSize: 11 },
          itemWidth: 10,
          itemHeight: 10,
        },
        grid: [
          { left: 56, right: 20, top: 32, bottom: '34%' },
          { left: 56, right: 20, top: '74%', bottom: 24 },
        ],
        xAxis: [
          {
            type: 'category',
            data: dates,
            gridIndex: 0,
            boundaryGap: false,
            axisLine: { lineStyle: { color: 'rgba(255,255,255,.1)' } },
            axisLabel: { color: '#5f6b85', fontSize: 10 },
            axisTick: { show: false },
          },
          {
            type: 'category',
            data: dates,
            gridIndex: 1,
            boundaryGap: false,
            axisLine: { lineStyle: { color: 'rgba(255,255,255,.1)' } },
            axisLabel: { color: '#5f6b85', fontSize: 10 },
            axisTick: { show: false },
          },
        ],
        yAxis: [
          {
            type: 'value',
            gridIndex: 0,
            axisLine: { show: false },
            axisLabel: { color: '#5f6b85', fontSize: 10, formatter: (v: number) => `${v.toFixed(1)}%` },
            splitLine: { lineStyle: { color: 'rgba(255,255,255,.05)' } },
          },
          {
            type: 'value',
            gridIndex: 1,
            max: 0,
            axisLine: { show: false },
            axisLabel: { color: '#5f6b85', fontSize: 10, formatter: (v: number) => `${v.toFixed(1)}%` },
            splitLine: { lineStyle: { color: 'rgba(255,255,255,.05)' } },
          },
        ],
        series: [
          {
            name: 'Equity (累计收益)',
            type: 'line',
            smooth: true,
            symbol: 'none',
            xAxisIndex: 0,
            yAxisIndex: 0,
            lineStyle: {
              width: 2.6,
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
            markArea: { silent: true, data: markAreas },
            markLine: { silent: true, symbol: 'none', data: markLines },
            data: navValues,
          },
          {
            name: 'Drawdown',
            type: 'line',
            smooth: true,
            symbol: 'none',
            xAxisIndex: 1,
            yAxisIndex: 1,
            lineStyle: { width: 1.4, color: '#ff5c7c' },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 1, 0, 0, [
                { offset: 0, color: 'rgba(255, 92, 124, 0.42)' },
                { offset: 1, color: 'rgba(255, 92, 124, 0)' },
              ]),
            },
            data: ddValues,
          },
        ],
      },
      true,
    )
  }, [dates, navValues, ddValues, splitIndex])

  if (!equity.length) {
    return <div className="bt-equity-empty">运行一次回测以查看净值曲线</div>
  }

  return <div className="bt-equity-canvas" ref={containerRef} />
}
