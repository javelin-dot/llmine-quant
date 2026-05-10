import { mock } from '../../data'

const STATUS_LABEL: Record<string, string> = {
  enforced: '已强制',
  enabled: '已启用',
  disabled: '已禁用',
}

export default function WithdrawalGuard() {
  const w = mock.security.withdrawal

  return (
    <div className="security-withdrawal">
      <div className="sw-head">
        <div>
          <h4 className="sw-title">提现防火墙 · Withdrawal Guard</h4>
          <span className="sw-sub">
            {w.enabled ? <em className="warn">提现 ON</em> : <em className="ok">提现 OFF · API 物理不开放</em>}
            <span> · 24h 拦截 {w.blocks24h}</span>
          </span>
        </div>
        <button className="sw-btn">查看出金账本</button>
      </div>

      <div className="sw-stats">
        <div className="sw-stat tone-green">
          <small>提现状态</small>
          <strong>{w.enabled ? 'ENABLED' : 'OFF'}</strong>
          <em>API scope 物理不含 withdrawal</em>
        </div>
        <div className="sw-stat tone-blue">
          <small>白名单地址</small>
          <strong>{w.whitelistAddresses}</strong>
          <em>{w.whitelistAddresses === 0 ? '券商柜台办理' : 'KYC 钱包预登记'}</em>
        </div>
        <div className={w.pendingApprovals > 0 ? 'sw-stat tone-yellow' : 'sw-stat tone-green'}>
          <small>待审批</small>
          <strong>{w.pendingApprovals}</strong>
          <em>{w.pendingApprovals === 0 ? '无人工审批排队' : '待 CFO 三签'}</em>
        </div>
        <div className={w.blocks24h > 0 ? 'sw-stat tone-yellow' : 'sw-stat tone-green'}>
          <small>24h 拦截</small>
          <strong>{w.blocks24h}</strong>
          <em>{w.lastBlock}</em>
        </div>
      </div>

      <div className="sw-rules">
        <h5 className="sw-rules-title">物理与流程规则</h5>
        <ul className="sw-rules-list">
          {w.rules.map((r, i) => (
            <li key={i} className={`sw-rule status-${r.statusTone}`}>
              <div className="sw-rule-info">
                <strong>{r.name}</strong>
                <span>{r.desc}</span>
              </div>
              <span className={`sw-rule-status pill-${r.statusTone}`}>
                <i />
                {STATUS_LABEL[r.status]}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
