import { mock } from '../../data'

const TYPE_LABEL: Record<string, string> = {
  live: '开仓',
  paper: '模拟',
  reduce: '减仓',
  add: '加仓',
  rotate: '轮换',
  hedge: '对冲',
  pause: '暂停',
}

const TYPE_ICON: Record<string, string> = {
  live: '▲',
  paper: '◇',
  reduce: '↓',
  add: '↑',
  rotate: '⇄',
  hedge: '⛨',
  pause: '⏸',
}

const SIDE_LABEL: Record<string, string> = {
  BUY: '买入',
  SELL: '卖出',
  PAUSE: '暂停',
}

function fmtCountdown(s: number): string {
  if (s < 0) return '已过期'
  const m = Math.floor(s / 60)
  const sec = s % 60
  return `${m}:${sec.toString().padStart(2, '0')}`
}

interface QueueProps {
  onModal?: (target: string) => void
}

export default function ApprovalQueue({ onModal }: QueueProps) {
  const list = mock.execution.approvals

  return (
    <div className="ex-approval-queue">
      <div className="ex-queue-head">
        <div>
          <h4 className="ex-queue-title">待审批队列 · Approval Queue</h4>
          <span className="ex-queue-sub">{list.length} 条 · 倒计时过期自动转人工</span>
        </div>
        <div className="ex-queue-actions">
          <button className="ex-queue-batch" onClick={() => onModal?.('approve')}>批量审批</button>
        </div>
      </div>
      <div className="ex-queue-grid">
        {list.map((a) => {
          const expired = a.expireSec < 0
          const critical = a.expireSec < 120
          return (
            <article
              className={`ex-approval-card type-${a.typeTone} urgency-${a.urgencyTone} ${expired ? 'expired' : ''}`}
              key={a.id}
            >
              <header className="ex-approval-card-head">
                <span className={`ex-approval-icon icon-${a.typeTone}`}>{TYPE_ICON[a.type]}</span>
                <div className="ex-approval-type">
                  <strong>{TYPE_LABEL[a.type]} · {SIDE_LABEL[a.side]}</strong>
                  <span className={`ex-urgency-pill tone-${a.urgencyTone}`}>
                    {a.urgency === 'high' ? '紧急' : a.urgency === 'medium' ? '一般' : '可延后'}
                  </span>
                </div>
                <div className={`ex-approval-countdown ${critical ? 'critical' : ''}`}>
                  <i className="ex-approval-clock" />
                  {fmtCountdown(a.expireSec)}
                </div>
              </header>

              <div className="ex-approval-symbol">
                <code>{a.symbol}</code>
                <strong>{a.name}</strong>
                <span className="ex-approval-strategy">{a.strategy}</span>
              </div>

              <div className="ex-approval-grid">
                <div className="ex-approval-cell">
                  <small>数量</small>
                  <strong>{a.qty}</strong>
                </div>
                <div className="ex-approval-cell">
                  <small>名义金额</small>
                  <strong>{a.notional}</strong>
                  {a.notionalPct > 0 && <em>{(a.notionalPct * 100).toFixed(1)}% 仓位</em>}
                </div>
                <div className="ex-approval-cell">
                  <small>限价</small>
                  <strong>{a.limitPrice}</strong>
                </div>
                <div className="ex-approval-cell">
                  <small>止损</small>
                  <strong className="ex-approval-stop">{a.stopLoss}</strong>
                </div>
              </div>

              <p className="ex-approval-reason">{a.reason}</p>

              <div className="ex-approval-stats">
                <div className="ex-approval-conf">
                  <span>置信度</span>
                  <div className="ex-approval-conf-bar">
                    <span style={{ width: `${a.confidence * 100}%` }} />
                  </div>
                  <em>{(a.confidence * 100).toFixed(0)}%</em>
                </div>
                <div className="ex-approval-grade">
                  <span>风控评分</span>
                  <strong className={`grade-${a.riskGrade.charAt(0).toLowerCase()}`}>{a.riskGrade}</strong>
                </div>
              </div>

              <div className="ex-approval-impact">
                <span>影响估算</span>
                <em>{a.impact}</em>
              </div>

              <div className="ex-approval-actions">
                <button className="ex-approval-btn primary" onClick={() => onModal?.('approve')}>批准</button>
                <button className="ex-approval-btn warn" onClick={() => onModal?.('pause')}>拒绝</button>
                <button className="ex-approval-btn ghost">推迟</button>
                <button className="ex-approval-btn ghost">详情</button>
              </div>
            </article>
          )
        })}
      </div>
    </div>
  )
}
