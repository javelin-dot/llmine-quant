import { mock } from '../../data'

export default function DecisionChain() {
  const chain = mock.explain.decisionChain
  return (
    <div className="ex-chain">
      <div className="ex-chain-head">
        <div>
          <h4 className="ex-chain-title">决策链 · Decision Chain</h4>
          <span className="ex-chain-sub">触发 → 风控 → 负面 → 最终动作</span>
        </div>
      </div>
      <div className="ex-chain-flow">
        {chain.map((c, i) => (
          <div key={i} className="ex-chain-cell-wrap">
            <div className={`ex-chain-cell tone-${c.tone}`}>
              <div className="ex-chain-step">
                <span className="ex-chain-num">{String(c.step).padStart(2, '0')}</span>
                <span className={`ex-chain-tag tag-${c.tone}`}>{c.tag}</span>
              </div>
              <strong className="ex-chain-cell-title">{c.title}</strong>
              <span className="ex-chain-desc">{c.desc}</span>
              <span className="ex-chain-detail">{c.detail}</span>
            </div>
            {i < chain.length - 1 && (
              <svg className="ex-chain-arrow" viewBox="0 0 32 24" fill="none">
                <path
                  d="M2 12 H 24"
                  stroke="rgba(76,141,255,0.55)"
                  strokeWidth="1.6"
                  strokeDasharray="3 3"
                />
                <path d="M22 6 L 28 12 L 22 18 Z" fill="rgba(76,141,255,0.65)" />
              </svg>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
