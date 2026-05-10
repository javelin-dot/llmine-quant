import { useMemo } from 'react'
import { mock } from '../../data'

export default function AttributionWaterfall() {
  const a = mock.explain.attribution

  const { steps, maxAbs } = useMemo(() => {
    const arr: { name: string; from: number; to: number; delta: number; desc?: string; type: 'base' | 'pos' | 'neg' | 'final' }[] = []
    let running = a.base
    arr.push({ name: '基线分', from: 0, to: a.base, delta: a.base, type: 'base' })
    a.items.forEach((item) => {
      const from = running
      running += item.value
      arr.push({
        name: item.name,
        from,
        to: running,
        delta: item.value,
        desc: item.desc,
        type: item.value >= 0 ? 'pos' : 'neg',
      })
    })
    arr.push({ name: '最终分', from: 0, to: a.final, delta: a.final, type: 'final' })
    const max = Math.max(...arr.map((s) => Math.max(Math.abs(s.from), Math.abs(s.to))))
    return { steps: arr, maxAbs: max || 1 }
  }, [a])

  const barH = 26
  const barGap = 30

  return (
    <div className="ex-attribution">
      <div className="ex-attr-head">
        <div>
          <h4 className="ex-attr-title">归因瀑布 · Why this signal</h4>
          <span className="ex-attr-sub">基线 → 因子贡献 → 最终决策</span>
        </div>
        <div className={`ex-attr-decision tone-${a.decisionTone}`}>
          <span>决策</span>
          <strong>{a.decision}</strong>
          <em>{a.final.toFixed(2)}</em>
        </div>
      </div>

      <div className="ex-attr-chart">
        {steps.map((s, i) => {
          const fromPct = (s.from / maxAbs) * 100
          const toPct = (s.to / maxAbs) * 100
          const left = Math.min(fromPct, toPct)
          const width = Math.abs(toPct - fromPct)
          return (
            <div className="ex-attr-row" key={i} style={{ height: `${barH + barGap}px` }}>
              <div className="ex-attr-label">{s.name}</div>
              <div className="ex-attr-track">
                <div className="ex-attr-zero" />
                <div
                  className={`ex-attr-bar bar-${s.type}`}
                  style={{
                    left: `${left}%`,
                    width: `${width}%`,
                  }}
                >
                  <span className="ex-attr-value">
                    {s.type === 'base' || s.type === 'final'
                      ? s.delta.toFixed(2)
                      : `${s.delta >= 0 ? '+' : ''}${s.delta.toFixed(2)}`}
                  </span>
                </div>
                {i < steps.length - 1 && (
                  <div
                    className="ex-attr-tie"
                    style={{
                      left: `${toPct}%`,
                    }}
                  />
                )}
              </div>
              <div className="ex-attr-desc">{s.desc ?? ''}</div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
