import { mock } from '../../data'

const STATUS_LABEL: Record<string, string> = {
  filled: '已成交',
  partial: '部分成交',
  rejected: '已拒单',
  canceled: '已撤单',
  working: '挂单中',
}

const STATUS_ICON: Record<string, string> = {
  filled: '✓',
  partial: '◐',
  rejected: '✕',
  canceled: '↻',
  working: '⏱',
}

export default function OrderBook() {
  const orders = mock.execution.orderBook
  const isCny = mock.portfolio.nav.currency === 'CNY'
  const ccy = isCny ? '¥' : '$'

  return (
    <div className="ex-orderbook">
      <div className="ex-orderbook-head">
        <div>
          <h4 className="ex-orderbook-title">订单流 · Order Book</h4>
          <span className="ex-orderbook-sub">{orders.length} 条 · 最近 5 分钟</span>
        </div>
        <div className="ex-orderbook-legend">
          {(['filled', 'partial', 'working', 'rejected', 'canceled'] as const).map((s) => (
            <span className={`ex-ob-legend-pill tone-${s}`} key={s}>
              <i className={`ex-ob-dot dot-${s}`} />
              {STATUS_LABEL[s]}
            </span>
          ))}
        </div>
      </div>
      <div className="ex-orderbook-table">
        <div className="ex-ob-row ex-ob-head">
          <span>时间</span>
          <span>标的</span>
          <span>方向</span>
          <span>数量</span>
          <span>限价</span>
          <span>已成交</span>
          <span>状态</span>
          <span>滑点</span>
          <span>P&amp;L</span>
        </div>
        {orders.map((o, i) => (
          <div className={`ex-ob-row tone-${o.statusTone}`} key={i}>
            <span className="ex-ob-time">{o.time}</span>
            <code className="ex-ob-symbol">{o.symbol}</code>
            <span className={`ex-ob-side ${o.side === 'BUY' ? 'buy' : 'sell'}`}>
              {o.side === 'BUY' ? '买' : '卖'}
            </span>
            <span className="ex-ob-qty">{o.qty}</span>
            <span className="ex-ob-limit">{o.limit}</span>
            <span className={`ex-ob-filled ${o.filled === '0' ? 'zero' : ''}`}>{o.filled}</span>
            <span className={`ex-ob-status tone-${o.statusTone}`}>
              <i>{STATUS_ICON[o.status]}</i>
              {STATUS_LABEL[o.status]}
            </span>
            <span className={`ex-ob-slip ${o.slippageBps < 0 ? 'pos' : o.slippageBps > 0 ? 'neg' : 'zero'}`}>
              {o.slippageBps === 0 ? '—' : `${o.slippageBps > 0 ? '+' : ''}${o.slippageBps.toFixed(1)}bp`}
            </span>
            <span className={`ex-ob-pnl ${o.pnl === null ? 'zero' : o.pnl >= 0 ? 'pos' : 'neg'}`}>
              {o.pnl === null
                ? '—'
                : `${o.pnl >= 0 ? '+' : ''}${ccy}${Math.abs(o.pnl) >= 1000 ? `${(o.pnl / 1000).toFixed(1)}K` : Math.abs(o.pnl).toFixed(0)}`}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
