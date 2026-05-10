import { mock } from '../../data'

const ROLE_ICON: Record<string, string> = {
  custody: '◆',
  'live-main': '◇',
  'live-small': '◇',
  paper: '◌',
  sandbox: '◯',
}

export default function AccountSegments() {
  const accounts = mock.security.accounts

  return (
    <div className="security-accounts">
      <div className="sa-head">
        <div>
          <h4 className="sa-title">账户分层 · Account Segmentation</h4>
          <span className="sa-sub">{accounts.length} 个账户 · 资金/实盘/小额/模拟/沙盒 物理隔离</span>
        </div>
        <button className="sa-btn">查看资金结构</button>
      </div>

      <div className="sa-list">
        {accounts.map((a) => {
          const capWarn = a.capPct >= 90
          const capWatch = a.capPct >= 70 && a.capPct < 90
          return (
            <article className={`sa-row tone-${a.roleTone}`} key={a.id}>
              <div className="sa-rail">
                <span className={`sa-icon tone-${a.roleTone}`}>{ROLE_ICON[a.role]}</span>
                <span className={`sa-role tone-${a.roleTone}`}>{a.roleLabel}</span>
              </div>
              <div className="sa-card">
                <header className="sa-card-head">
                  <div className="sa-card-title">
                    <strong>{a.name}</strong>
                    {!a.withdrawalEnabled && <span className="sa-no-withdraw">提现 OFF</span>}
                  </div>
                  <div className="sa-balance">
                    <strong>{a.balance}</strong>
                    <em>{a.balanceUsd}</em>
                  </div>
                </header>
                <p className="sa-desc">{a.desc}</p>
                {a.cap !== 'unlimited' && a.cap !== 'n/a' && (
                  <div className="sa-cap">
                    <div className="sa-cap-meta">
                      <small>资金上限</small>
                      <code>{a.cap}</code>
                      <span className={capWarn ? 'sa-cap-pct warn' : capWatch ? 'sa-cap-pct watch' : 'sa-cap-pct'}>
                        {a.capPct}%
                      </span>
                    </div>
                    <div className="sa-cap-bar">
                      <i
                        className={capWarn ? 'warn' : capWatch ? 'watch' : ''}
                        style={{ width: `${Math.min(a.capPct, 100)}%` }}
                      />
                    </div>
                  </div>
                )}
                <div className="sa-perms">
                  <small>AI 权限</small>
                  {a.aiPermissions.map((p, i) => (
                    <span className={`sa-perm tone-${p.tone}`} key={i}>
                      {p.label}
                    </span>
                  ))}
                </div>
              </div>
            </article>
          )
        })}
      </div>
    </div>
  )
}
