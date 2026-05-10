import { useExplain } from '../../contexts/ExplainContext'

export default function LineageGraph() {
  const data = useExplain()
  const lineage = data.lineage
  return (
    <div className="ex-lineage">
      <div className="ex-lineage-head">
        <div>
          <h4 className="ex-lineage-title">数据血缘 · Lineage</h4>
          <span className="ex-lineage-sub">Raw → Cleaning → Feature → Bias → Backtest → Signal → Order</span>
        </div>
        <div className="ex-lineage-legend">
          <span><i className="dot-green" /> Live</span>
          <span><i className="dot-yellow" /> HITL</span>
          <span><i className="dot-blue" /> Research</span>
        </div>
      </div>
      <div className="ex-lineage-flow">
        {lineage.map((node, i) => (
          <div key={i} className="ex-lineage-node-wrap">
            <div className={`ex-lineage-node tone-${node.permissionTone}`}>
              <div className="ex-lineage-node-head">
                <span className={`ex-lineage-perm perm-${node.permissionTone}`}>{node.permission}</span>
                <code className="ex-lineage-hash">#{node.hash}</code>
              </div>
              <strong className="ex-lineage-step">{node.step}</strong>
              <span className="ex-lineage-version">{node.version}</span>
              <span className="ex-lineage-detail">{node.detail}</span>
            </div>
            {i < lineage.length - 1 && (
              <svg className="ex-lineage-arrow" viewBox="0 0 24 16" fill="none">
                <path d="M0 8 H 18" stroke="rgba(76,141,255,0.5)" strokeWidth="1.4" />
                <path d="M16 3 L 22 8 L 16 13 Z" fill="rgba(76,141,255,0.6)" />
              </svg>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
