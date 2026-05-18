import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'
import { useExplain } from '../../contexts/ExplainContext'

export default function ConfidenceRadar() {
  const data = useExplain()
  const containerRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<echarts.ECharts | null>(null)
  const r = data.confidenceRadar

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
    chart.setOption({
      animationDuration: 700,
      animationEasing: 'cubicOut',
      tooltip: {
        backgroundColor: 'rgba(15, 21, 43, 0.94)',
        borderColor: 'rgba(76, 141, 255, 0.4)',
        borderWidth: 1,
        textStyle: { color: '#eef4ff', fontSize: 12 },
      },
      radar: {
        center: ['50%', '54%'],
        radius: '64%',
        splitNumber: 4,
        axisName: {
          color: '#cad4ee',
          fontSize: 11,
          padding: [3, 6],
          backgroundColor: 'rgba(76,141,255,0.12)',
          borderRadius: 6,
        },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
        splitArea: { areaStyle: { color: ['rgba(76,141,255,0.04)', 'rgba(76,141,255,0.01)'] } },
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
        indicator: r.axes.map((a) => ({ name: a.name, max: 1 })),
      },
      series: [
        {
          type: 'radar',
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: {
            width: 2,
            color: new echarts.graphic.LinearGradient(0, 0, 1, 1, [
              { offset: 0, color: '#42e8ff' },
              { offset: 1, color: '#4ff0a2' },
            ]),
          },
          areaStyle: {
            color: new echarts.graphic.RadialGradient(0.5, 0.5, 0.6, [
              { offset: 0, color: 'rgba(66,232,255,0.36)' },
              { offset: 1, color: 'rgba(66,232,255,0.02)' },
            ]),
          },
          itemStyle: { color: '#42e8ff', borderColor: '#0b1226', borderWidth: 2 },
          data: [
            {
              value: r.axes.map((a) => a.score),
              name: 'Confidence',
            },
          ],
        },
      ],
    })
  }, [r])

  return (
    <div className="ex-radar">
      <div className="ex-radar-head">
        <div>
          <h4 className="ex-radar-title">置信度雷达 · 4 维交叉验证</h4>
          <span className="ex-radar-sub">数据 · 历史 · 执行 · 风险</span>
        </div>
        <div className="ex-radar-avg">
          <span>综合</span>
          <strong>{(r.avg * 100).toFixed(0)}</strong>
          <em>/ 100</em>
        </div>
      </div>
      <div className="ex-radar-body">
        <div className="ex-radar-canvas" ref={containerRef} />
        <ul className="ex-radar-list">
          {r.axes.map((a, i) => {
            const tone = a.score >= 0.85 ? 'green' : a.score >= 0.7 ? 'yellow' : 'red'
            return (
              <li key={i} className={`ex-radar-axis tone-${tone}`}>
                <div className="ex-radar-axis-head">
                  <strong>{a.name}</strong>
                  <span>{(a.score * 100).toFixed(0)}</span>
                </div>
                <p>{a.desc}</p>
              </li>
            )
          })}
        </ul>
      </div>
    </div>
  )
}
