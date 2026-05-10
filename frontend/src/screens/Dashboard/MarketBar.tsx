import { mock } from '../../data'

function formatPrice(value: number): string {
  if (value >= 1e12) return `${(value / 1e12).toFixed(2)}T`
  if (value >= 1e9) return `${(value / 1e9).toFixed(2)}B`
  if (value >= 1e6) return `${(value / 1e6).toFixed(2)}M`
  if (value >= 10000) return value.toLocaleString('en-US', { maximumFractionDigits: 2 })
  return value.toFixed(2)
}

export default function MarketBar() {
  return (
    <div className="market-bar">
      <div className="market-bar-track">
        {mock.dashboard.marketIndices.map((idx) => {
          const positive = idx.change >= 0
          return (
            <div className="market-tick" key={idx.symbol}>
              <span className="market-tick-name">{idx.name}</span>
              <span className="market-tick-price">{formatPrice(idx.price)}</span>
              <span className={`market-tick-change ${positive ? 'up' : 'down'}`}>
                {positive ? '▲' : '▼'} {Math.abs(idx.change).toFixed(2)}%
              </span>
              <span className="market-tick-vol">成交 {idx.volume}</span>
            </div>
          )
        })}
      </div>
      <div className="market-bar-clock">
        <span className="market-bar-dot" />
        实时行情
      </div>
    </div>
  )
}
