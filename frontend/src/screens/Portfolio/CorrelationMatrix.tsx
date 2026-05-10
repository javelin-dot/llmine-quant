import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'
import { mock } from '../../data'

export default function CorrelationMatrix() {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<echarts.ECharts | null>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const pendingOptionRef = useRef<any>(null)
  const c = mock.portfolio.correlation

  useEffect(() => {
    if (!containerRef.current) return
    const el = containerRef.current

    const initOrResize = () => {
      if (!chartRef.current) {
        const rect = el.getBoundingClientRect()
        if (rect.width > 0 && rect.height > 0) {
          chartRef.current = echarts.init(el, undefined, { renderer: 'canvas' })
          if (pendingOptionRef.current) {
            chartRef.current.setOption(pendingOptionRef.current, true)
          }
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
    const data: [number, number, number][] = []
    for (let i = 0; i < c.labels.length; i++) {
      for (let j = 0; j < c.labels.length; j++) {
        data.push([j, i, c.matrix[i][j]])
      }
    }

    const option = {
      animationDuration: 700,
      tooltip: {
        backgroundColor: 'rgba(15, 21, 43, 0.94)',
        borderColor: 'rgba(76, 141, 255, 0.4)',
        borderWidth: 1,
        textStyle: { color: '#eef4ff', fontSize: 12 },
        formatter: (p: { value: [number, number, number] }) => {
          const [x, y, v] = p.value
          return `<b>${c.labels[y]} × ${c.labels[x]}</b><br/>相关性 ${v.toFixed(2)}`
        },
      },
      grid: { left: 60, right: 24, top: 32, bottom: 60, containLabel: false },
      xAxis: {
        type: 'category',
        data: c.labels,
        splitArea: { show: false },
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
        axisLabel: { color: '#cad4ee', fontSize: 11, fontWeight: 600, rotate: 0 },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'category',
        data: c.labels,
        splitArea: { show: false },
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
        axisLabel: { color: '#cad4ee', fontSize: 11, fontWeight: 600 },
        axisTick: { show: false },
        inverse: true,
      },
      visualMap: {
        min: 0,
        max: 1,
        calculable: false,
        show: false,
        inRange: {
          color: [
            'rgba(76, 141, 255, 0.18)',
            'rgba(66, 232, 255, 0.4)',
            'rgba(255, 209, 102, 0.6)',
            'rgba(255, 154, 76, 0.7)',
            'rgba(255, 92, 124, 0.85)',
          ],
        },
      },
      series: [
        {
          name: 'Correlation',
          type: 'heatmap',
          data,
          label: {
            show: true,
            color: '#0b1226',
            fontSize: 10,
            fontWeight: 700,
            formatter: (p: { value: [number, number, number] }) => {
              const v = p.value[2]
              if (v === 1) return '1.0'
              return v.toFixed(2).replace('0.', '.')
            },
          },
          emphasis: {
            itemStyle: {
              borderColor: '#42e8ff',
              borderWidth: 2,
              shadowBlur: 8,
              shadowColor: 'rgba(66, 232, 255, 0.6)',
            },
          },
          itemStyle: {
            borderRadius: 4,
            borderColor: 'rgba(11, 18, 38, 0.6)',
            borderWidth: 1.5,
          },
        },
      ],
    }
    pendingOptionRef.current = option
    if (chartRef.current) {
      chartRef.current.setOption(option, true)
    }
  }, [c])

  return (
    <div className="pf-correlation">
      <div className="pf-correlation-head">
        <div>
          <h4 className="pf-correlation-title">策略相关性 · Correlation</h4>
          <span className="pf-correlation-sub">{c.labels.length} × {c.labels.length} · 蓝→低,红→高</span>
        </div>
        <div className="pf-correlation-legend">
          <span className="pf-legend-bar" />
          <em>0.0</em>
          <em>0.5</em>
          <em>1.0</em>
        </div>
      </div>
      <div className="pf-correlation-body" ref={containerRef} />
    </div>
  )
}
