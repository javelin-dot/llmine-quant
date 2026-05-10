import { useEffect, useMemo, useRef } from 'react'
import * as echarts from 'echarts'
import { mock } from '../../data'

const STRATEGY_COLORS = ['#4c8dff', '#42e8ff', '#4ff0a2', '#a98bff', '#ffd166', '#ff8a4c', '#ff5c7c', '#5f6b85']

export default function AllocationDonut() {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<echarts.ECharts | null>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const pendingOptionRef = useRef<any>(null)
  const strategies = mock.portfolio.allocation.strategies

  const totalPnl = useMemo(() => strategies.reduce((s, x) => s + x.pnl, 0), [strategies])
  const isCny = mock.portfolio.nav.currency === 'CNY'
  const ccy = isCny ? '¥' : '$'

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
    const option = {
      animationDuration: 800,
      animationEasing: 'cubicOut' as const,
      tooltip: {
        backgroundColor: 'rgba(15, 21, 43, 0.94)',
        borderColor: 'rgba(76, 141, 255, 0.4)',
        borderWidth: 1,
        textStyle: { color: '#eef4ff', fontSize: 12 },
        formatter: (p: { name: string; value: number; percent: number; color: string }) => {
          return `<b style="color:${p.color}">${p.name}</b><br/>权重 ${(p.percent).toFixed(1)}%`
        },
      },
      series: [
        {
          name: '策略分配',
          type: 'pie',
          radius: ['52%', '78%'],
          center: ['50%', '50%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 4,
            borderColor: '#0b1226',
            borderWidth: 2,
          },
          label: { show: false },
          labelLine: { show: false },
          data: strategies.map((s, i) => ({
            value: +(s.weight * 100).toFixed(1),
            name: s.name,
            itemStyle: { color: STRATEGY_COLORS[i % STRATEGY_COLORS.length] },
          })),
        },
      ],
    }
    pendingOptionRef.current = option
    if (chartRef.current) {
      chartRef.current.setOption(option, true)
    }
  }, [strategies])

  return (
    <div className="pf-allocation">
      <div className="pf-allocation-head">
        <div>
          <h4 className="pf-allocation-title">策略分配 · Allocation</h4>
          <span className="pf-allocation-sub">{strategies.length} 个策略 · 总贡献 {ccy}{(totalPnl / 1000).toFixed(1)}K</span>
        </div>
      </div>
      <div className="pf-allocation-body">
        <div className="pf-donut-wrap">
          <div className="pf-donut" ref={containerRef} />
          <div className="pf-donut-center">
            <span className="pf-donut-label">总收益</span>
            <strong className={totalPnl >= 0 ? 'pos' : 'neg'}>
              {totalPnl >= 0 ? '+' : ''}
              {ccy}
              {(totalPnl / 1000).toFixed(1)}K
            </strong>
            <span className="pf-donut-sub">8 strategies</span>
          </div>
        </div>
        <div className="pf-strategy-table">
          <div className="pf-strategy-head">
            <span>策略</span>
            <span>权重</span>
            <span>P&amp;L</span>
            <span>贡献</span>
            <span>状态</span>
          </div>
          {strategies.map((s, i) => (
            <div className="pf-strategy-row" key={s.name}>
              <div className="pf-strategy-name">
                <span className="pf-strategy-dot" style={{ background: STRATEGY_COLORS[i % STRATEGY_COLORS.length] }} />
                <div>
                  <strong>{s.name}</strong>
                  <small>{s.family} · {s.risk}</small>
                </div>
              </div>
              <div className="pf-strategy-weight">
                <span>{(s.weight * 100).toFixed(0)}%</span>
                <div className="pf-strategy-weight-bar">
                  <span style={{ width: `${s.weight * 100}%`, background: STRATEGY_COLORS[i % STRATEGY_COLORS.length] }} />
                </div>
              </div>
              <div className={`pf-strategy-pnl ${s.pnl >= 0 ? 'pos' : 'neg'}`}>
                {s.pnl >= 0 ? '+' : ''}
                {ccy}
                {Math.abs(s.pnl) >= 1000 ? `${(s.pnl / 1000).toFixed(1)}K` : Math.abs(s.pnl).toFixed(0)}
                <small>{s.pnlPct >= 0 ? '+' : ''}{(s.pnlPct * 100).toFixed(1)}%</small>
              </div>
              <div className={`pf-strategy-contrib ${s.contribution >= 0 ? 'pos' : 'neg'}`}>
                {s.contribution >= 0 ? '+' : ''}
                {(s.contribution * 100).toFixed(0)}%
              </div>
              <div className="pf-strategy-status">
                <span className={`pf-status-pill tone-${s.statusTone}`}>
                  <i className={`status-dot-${s.statusTone}`} />
                  {s.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
