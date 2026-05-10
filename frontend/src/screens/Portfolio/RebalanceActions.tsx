import { usePortfolio } from '../../contexts/PortfolioContext'

const TYPE_LABEL: Record<string, string> = {
  reduce: '减仓',
  add: '加仓',
  rotate: '轮换',
  hedge: '对冲',
}

const TYPE_ICON: Record<string, string> = {
  reduce: '↓',
  add: '↑',
  rotate: '⇄',
  hedge: '⛨',
}

const TYPE_TONE: Record<string, 'red' | 'green' | 'blue' | 'purple'> = {
  reduce: 'red',
  add: 'green',
  rotate: 'blue',
  hedge: 'purple',
}

interface RebalanceProps {
  onModal?: (target: string) => void
}

export default function RebalanceActions({ onModal }: RebalanceProps) {
  const data = usePortfolio()
  const actions = data.rebalance
  return (
    <div className="pf-rebalance">
      <div className="pf-rebalance-head">
        <div>
          <h4 className="pf-rebalance-title">调仓建议 · Rebalance Queue</h4>
          <span className="pf-rebalance-sub">{actions.length} 条 AI 推荐 · 等待人工审批</span>
        </div>
        <button className="pf-rebalance-btn" onClick={() => onModal?.('approve')}>批量审批</button>
      </div>
      <div className="pf-rebalance-grid">
        {actions.map((a) => {
          const typeTone = TYPE_TONE[a.type]
          return (
            <div key={a.id} className={`pf-rebalance-card type-${typeTone} urgency-${a.urgencyTone}`}>
              <div className="pf-rebalance-card-head">
                <div className={`pf-rebalance-icon icon-${typeTone}`}>{TYPE_ICON[a.type]}</div>
                <div className="pf-rebalance-type">
                  <strong>{TYPE_LABEL[a.type]}</strong>
                  <span className={`pf-urgency-pill tone-${a.urgencyTone}`}>
                    {a.urgency === 'high' ? '紧急' : a.urgency === 'medium' ? '一般' : '可延后'}
                  </span>
                </div>
                <div className="pf-rebalance-delta">
                  <span>{a.delta}</span>
                </div>
              </div>
              <div className="pf-rebalance-flow">
                <span className="pf-rebalance-from">{a.from}</span>
                <svg className="pf-rebalance-arrow" viewBox="0 0 32 16" fill="none">
                  <path d="M0 8 H 24" stroke="rgba(76,141,255,0.5)" strokeWidth="1.4" />
                  <path d="M22 3 L 28 8 L 22 13 Z" fill="rgba(76,141,255,0.6)" />
                </svg>
                <span className="pf-rebalance-to">{a.to}</span>
              </div>
              <p className="pf-rebalance-reason">{a.reason}</p>
              <div className="pf-rebalance-impact">
                <span>影响</span>
                <em>{a.impact}</em>
              </div>
              <div className="pf-rebalance-actions">
                <button className="pf-rebalance-action primary" onClick={() => onModal?.('approve')}>批准</button>
                <button className="pf-rebalance-action secondary">推迟</button>
                <button className="pf-rebalance-action ghost">详情</button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
