import { useMemo } from 'react'
import { useData } from '../../contexts/DataContext'

const TIER_PREF = ['raw', 'feature', 'model', 'signal', 'order'] as const

const TIER_LABEL: Record<string, string> = {
  raw: '原始数据',
  feature: '特征因子',
  model: '模型',
  signal: '信号',
  order: '订单',
}

const W = 1100
const H = 360
const PAD_X = 80
const PAD_Y = 40

function tierLabel(tier: string): string {
  return TIER_LABEL[tier] ?? tier
}

function dlgLegClass(tier: string): string {
  if (TIER_PREF.includes(tier as (typeof TIER_PREF)[number])) return `leg-${tier}`
  return 'leg-other'
}

function orderedTiers(nodeTiers: string[]): string[] {
  const uniq = [...new Set(nodeTiers)]
  const known = TIER_PREF.filter((t) => uniq.includes(t))
  const extra = uniq.filter((t) => !TIER_PREF.includes(t as (typeof TIER_PREF)[number])).sort()
  return [...known, ...extra]
}

export default function LineageGraph() {
  const data = useData()
  const { nodes, edges } = data.lineage

  const { tiersOrdered, positions, colPositions } = useMemo(() => {
    const tiers = orderedTiers(nodes.map((n) => n.tier))
    const byTier: Record<string, typeof nodes> = {}
    tiers.forEach((t) => {
      byTier[t] = []
    })
    nodes.forEach((n) => {
      const list = byTier[n.tier] ?? []
      list.push(n)
      byTier[n.tier] = list
    })

    const colCount = tiers.length
    const colWidth = colCount <= 1 ? 0 : (W - PAD_X * 2) / (colCount - 1)
    const xs: Record<string, number> = {}
    tiers.forEach((tier, colIdx) => {
      xs[tier] = colCount <= 1 ? W / 2 : PAD_X + colIdx * colWidth
    })

    const pos: Record<string, { x: number; y: number }> = {}
    tiers.forEach((tier) => {
      const ns = byTier[tier] ?? []
      const x = xs[tier]
      const colHeight = H - PAD_Y * 2
      const step = ns.length > 1 ? colHeight / (ns.length - 1) : 0
      ns.forEach((n, i) => {
        const y = ns.length === 1 ? H / 2 : PAD_Y + i * step
        pos[n.id] = { x, y }
      })
    })

    return { tiersOrdered: tiers, positions: pos, colPositions: xs }
  }, [nodes])

  return (
    <div className="data-lineage">
      <div className="dlg-head">
        <div>
          <h4 className="dlg-title">数据血缘 · Data Lineage</h4>
          <span className="dlg-sub">从行情入库到特征消费 · {nodes.length} 节点 · {edges.length} 边</span>
        </div>
        <div className="dlg-legend">
          {tiersOrdered.map((tier) => (
            <span key={tier} className={`dlg-leg ${dlgLegClass(tier)}`}>
              <i />
              {tierLabel(tier)}
            </span>
          ))}
        </div>
      </div>

      <div className="dlg-canvas">
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} preserveAspectRatio="xMidYMid meet">
          <defs>
            <linearGradient id="dlg-edge" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="rgba(124,198,255,0.6)" />
              <stop offset="100%" stopColor="rgba(124,198,255,0.18)" />
            </linearGradient>
            <marker id="dlg-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
              <path d="M0,0 L10,5 L0,10 Z" fill="rgba(124,198,255,0.5)" />
            </marker>
          </defs>

          {tiersOrdered.map((tier) => {
            const x = colPositions[tier]
            return (
              <g key={tier}>
                <text x={x} y={20} fontSize="11" fill="rgba(255,255,255,0.45)" textAnchor="middle" letterSpacing="2">
                  {tierLabel(tier).toUpperCase()}
                </text>
                <line x1={x} x2={x} y1={28} y2={H - 12} stroke="rgba(255,255,255,0.04)" strokeDasharray="2 4" />
              </g>
            )
          })}

          {edges.map((e, i) => {
            const a = positions[e.from]
            const b = positions[e.to]
            if (!a || !b) return null
            const cx1 = a.x + (b.x - a.x) * 0.5
            const cx2 = a.x + (b.x - a.x) * 0.5
            const path = `M${a.x + 38},${a.y} C${cx1},${a.y} ${cx2},${b.y} ${b.x - 38},${b.y}`
            return (
              <path
                key={i}
                d={path}
                fill="none"
                stroke="url(#dlg-edge)"
                strokeWidth="1.4"
                markerEnd="url(#dlg-arrow)"
                opacity={0.85}
              />
            )
          })}

          {nodes.map((n) => {
            const p = positions[n.id]
            if (!p) return null
            return (
              <g key={n.id} transform={`translate(${p.x - 56} ${p.y - 18})`}>
                <rect width="112" height="36" rx="9" className={`dlg-node node-${n.tone}`} />
                <text x="56" y="15" fontSize="10.5" fill="#ecf1ff" textAnchor="middle" fontWeight="600">
                  {n.label}
                </text>
                <text x="56" y="28" fontSize="8" fill="rgba(255,255,255,0.55)" textAnchor="middle">
                  {n.permission} · {n.version}
                </text>
              </g>
            )
          })}
        </svg>
      </div>
    </div>
  )
}
