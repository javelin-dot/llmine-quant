import { useEffect, useMemo, useRef } from 'react'
import * as echarts from 'echarts'
import { mock } from '../../data'

export default function EquityDivergence() {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<echarts.ECharts | null>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const pendingOptionRef = useRef<any>(null)

  const { dates, isValues, oosValues, ddValues, isReturn, oosReturn, stabilityRatio } = useMemo(() => {
    const c = mock.backtest.equityCurves
    const isMap = new Map(c.inSample.map((p) => [p.date, p.value]))
    const oosMap = new Map(c.outSample.map((p) => [p.date, p.value]))
    const ddMap = new Map(c.drawdown.map((p) => [p.date, p.value]))
    const allDates = Array.from(new Set([...isMap.keys(), ...oosMap.keys()]))
    allDates.sort()
    const isVals = allDates.map((d) => (isMap.has(d) ? +((isMap.get(d) as number) * 100 - 100).toFixed(2) : null))
    const oosVals = allDates.map((d) => (oosMap.has(d) ? +((oosMap.get(d) as number) * 100 - 100).toFixed(2) : null))
    const ddVals = allDates.map((d) => (ddMap.has(d) ? +((ddMap.get(d) as number) * 100).toFixed(2) : null))
    const isFirst = c.inSample[0].value
    const isLast = c.inSample[c.inSample.length - 1].value
    const oosFirst = c.outSample[0].value
    const oosLast = c.outSample[c.outSample.length - 1].value
    const isLen = c.inSample.length
    const oosLen = c.outSample.length
    const isPerWeek = (isLast / isFirst - 1) / Math.max(isLen - 1, 1)
    const oosPerWeek = (oosLast / oosFirst - 1) / Math.max(oosLen - 1, 1)
    const isReturnPct = (isLast / isFirst - 1) * 100
    const oosReturnPct = (oosLast / oosFirst - 1) * 100
    const stability = isPerWeek === 0 ? 0 : (oosPerWeek / isPerWeek) * 100
    return {
      dates: allDates,
      isValues: isVals,
      oosValues: oosVals,
      ddValues: ddVals,
      isReturn: isReturnPct,
      oosReturn: oosReturnPct,
      stabilityRatio: stability,
    }
  }, [])

  useEffect(() => {
    if (!containerRef.current) return
    const el = containerRef.current

    const applyOption = () => {
      if (chartRef.current && pendingOptionRef.current) {
        chartRef.current.setOption(pendingOptionRef.current, true)
      }
    }

    const initOrResize = () => {
      if (!chartRef.current) {
        const rect = el.getBoundingClientRect()
        if (rect.width > 0 && rect.height > 0) {
          chartRef.current = echarts.init(el, undefined, { renderer: 'canvas' })
          applyOption()
        }
      } else {
        chartRef.current.resize()
      }
    }

    initOrResize()
    const ro = new ResizeObserver(initOrResize)
    ro.observe(el)

    return () => {
      ro.disconnect()
      if (chartRef.current) {
        chartRef.current.dispose()
        chartRef.current = null
      }
    }
  }, [])

  useEffect(() => {
    const option = {
      animationDuration: 800,
      animationEasing: 'cubicOut',
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(15, 21, 43, 0.94)',
        borderColor: 'rgba(76, 141, 255, 0.4)',
        borderWidth: 1,
        textStyle: { color: '#eef4ff', fontSize: 12 },
        axisPointer: { type: 'cross', lineStyle: { color: 'rgba(66, 232, 255, 0.4)', type: 'dashed' } },
        valueFormatter: (v: number | null) => (v == null ? '—' : `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`),
      },
      legend: {
        data: ['Sample (IS)', 'Out-of-Sample (OOS)', 'Drawdown'],
        top: 0,
        right: 8,
        textStyle: { color: '#8f9bb7', fontSize: 11 },
        itemWidth: 10,
        itemHeight: 10,
      },
      grid: [
        { left: 48, right: 16, top: 32, bottom: '28%' },
        { left: 48, right: 16, top: '76%', bottom: 20 },
      ],
      xAxis: [
        {
          type: 'category',
          data: dates,
          gridIndex: 0,
          boundaryGap: false,
          axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
          axisLabel: { color: '#5f6b85', fontSize: 10 },
          axisTick: { show: false },
        },
        {
          type: 'category',
          data: dates,
          gridIndex: 1,
          boundaryGap: false,
          axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
          axisLabel: { color: '#5f6b85', fontSize: 10 },
          axisTick: { show: false },
        },
      ],
      yAxis: [
        {
          type: 'value',
          gridIndex: 0,
          axisLine: { show: false },
          axisLabel: { show: false },
          splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
        },
        {
          type: 'value',
          gridIndex: 1,
          max: 0,
          axisLine: { show: false },
          axisLabel: { show: false },
          splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
        },
      ],
      series: [
        {
          name: 'Sample (IS)',
          type: 'line',
          smooth: true,
          symbol: 'none',
          xAxisIndex: 0,
          yAxisIndex: 0,
          connectNulls: false,
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
          markPoint: {
            symbol: 'none',
            label: {
              show: true,
              color: '#4ff0a2',
              fontSize: 11,
              fontWeight: 600,
              formatter: (p: unknown) => `+${((p as { value: number }).value).toFixed(1)}%`,
              backgroundColor: 'rgba(15, 21, 43, 0.78)',
              borderColor: 'rgba(79, 240, 162, 0.35)',
              borderWidth: 1,
              borderRadius: 6,
              padding: [2, 6],
            },
            data: [{ type: 'max' as const }],
          },
          data: isValues,
        },
        {
          name: 'Out-of-Sample (OOS)',
          type: 'line',
          smooth: true,
          symbol: 'none',
          xAxisIndex: 0,
          yAxisIndex: 0,
          connectNulls: false,
          lineStyle: {
            width: 2.4,
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: '#ffd166' },
              { offset: 1, color: '#ff8a4c' },
            ]),
            type: 'solid',
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(255, 154, 76, 0.26)' },
              { offset: 1, color: 'rgba(255, 154, 76, 0)' },
            ]),
          },
          markPoint: {
            symbol: 'none',
            label: {
              show: true,
              color: '#ff9f43',
              fontSize: 11,
              fontWeight: 600,
              formatter: (p: unknown) => `+${((p as { value: number }).value).toFixed(1)}%`,
              backgroundColor: 'rgba(15, 21, 43, 0.78)',
              borderColor: 'rgba(255, 159, 67, 0.35)',
              borderWidth: 1,
              borderRadius: 6,
              padding: [2, 6],
            },
            data: [{ type: 'max' as const }],
          },
          data: oosValues,
        },
        {
          name: 'Drawdown',
          type: 'line',
          smooth: true,
          symbol: 'none',
          xAxisIndex: 1,
          yAxisIndex: 1,
          lineStyle: { width: 1.6, color: '#ff5c7c' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 1, 0, 0, [
              { offset: 0, color: 'rgba(255, 92, 124, 0.42)' },
              { offset: 1, color: 'rgba(255, 92, 124, 0)' },
            ]),
          },
          data: ddValues,
        },
      ],
    }
    pendingOptionRef.current = option
    if (chartRef.current) {
      chartRef.current.setOption(pendingOptionRef.current, true)
    }
  }, [dates, isValues, oosValues, ddValues])

  return (
    <div className="bt-equity">
      <div className="bt-equity-head">
        <div>
          <h4 className="bt-equity-title">Equity Divergence · IS vs OOS</h4>
          <span className="bt-equity-sub">{mock.backtest.equityCurves.label}</span>
        </div>
        <div className="bt-equity-pills">
          <div className="bt-equity-pill">
            <span>IS 收益</span>
            <strong className={isReturn >= 0 ? 'pos' : 'neg'}>
              {isReturn >= 0 ? '+' : ''}
              {isReturn.toFixed(1)}%
            </strong>
          </div>
          <div className="bt-equity-pill">
            <span>OOS 收益</span>
            <strong className={oosReturn >= 0 ? 'pos' : 'neg'}>
              {oosReturn >= 0 ? '+' : ''}
              {oosReturn.toFixed(1)}%
            </strong>
          </div>
          <div className={`bt-equity-pill divergence ${stabilityRatio < 60 ? 'warn' : ''}`}>
            <span>OOS / IS 稳定度</span>
            <strong>{stabilityRatio.toFixed(0)}%</strong>
          </div>
        </div>
      </div>
      <div className="bt-equity-canvas" ref={containerRef} />
    </div>
  )
}
