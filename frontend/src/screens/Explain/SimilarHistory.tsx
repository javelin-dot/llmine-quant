import { useExplain } from '../../contexts/ExplainContext'

export default function SimilarHistory() {
  const data = useExplain()
  const h = data.similarHistory
  const winRatePct = (h.winRate * 100).toFixed(1)
  const avgPct = (h.avgReturn * 100).toFixed(1)

  return (
    <div className="ex-similar">
      <div className="ex-similar-head">
        <div>
          <h4 className="ex-similar-title">相似历史 · Pattern Memory</h4>
          <span className="ex-similar-sub">{h.summary}</span>
        </div>
        <div className="ex-similar-stats">
          <div className="ex-similar-stat">
            <span>胜率</span>
            <strong className={h.winRate >= 0.6 ? 'pos' : 'neg'}>{winRatePct}%</strong>
          </div>
          <div className="ex-similar-stat">
            <span>平均收益</span>
            <strong className={h.avgReturn >= 0 ? 'pos' : 'neg'}>
              {h.avgReturn >= 0 ? '+' : ''}
              {avgPct}%
            </strong>
          </div>
          <div className="ex-similar-stat">
            <span>样本数</span>
            <strong>{h.cases.length}</strong>
          </div>
        </div>
      </div>
      <div className="ex-similar-grid">
        {h.cases.map((c) => {
          const retPct = (c.ret * 100).toFixed(1)
          return (
            <div key={c.id} className={`ex-similar-card ${c.success ? 'win' : 'loss'}`}>
              <div className="ex-similar-card-head">
                <span className="ex-similar-date">{c.date}</span>
                <span className={`ex-similar-pill ${c.success ? 'pos' : 'neg'}`}>
                  {c.ret >= 0 ? '+' : ''}
                  {retPct}%
                </span>
              </div>
              <strong className="ex-similar-action">{c.action} · {c.days}天</strong>
              <p className="ex-similar-note">{c.note}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
