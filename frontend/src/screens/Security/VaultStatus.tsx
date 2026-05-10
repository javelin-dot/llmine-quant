import { useState } from 'react'
import { mock } from '../../data'

const TYPE_ICON: Record<string, string> = {
  api: '⌬',
  wallet: '⚿',
  ssh: '⚙',
  webhook: '↺',
  db: '⛁',
}

const TYPE_LABEL: Record<string, string> = {
  api: 'API',
  wallet: 'Wallet',
  ssh: 'SSH',
  webhook: 'Webhook',
  db: 'DB',
}

const STATUS_LABEL: Record<string, string> = {
  active: '健康',
  rotating: '轮换中',
  expiring: '临期',
  expired: '已过期',
}

type TypeFilter = 'all' | 'api' | 'wallet' | 'ssh' | 'webhook' | 'db'

export default function VaultStatus() {
  const [filter, setFilter] = useState<TypeFilter>('all')
  const v = mock.security.vault
  const keys = v.keys
  const list = filter === 'all' ? keys : keys.filter((k) => k.type === filter)

  const counts = keys.reduce((acc, k) => {
    acc[k.type] = (acc[k.type] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  return (
    <div className="security-vault">
      <div className="sv-head">
        <div>
          <h4 className="sv-title">Vault & 密钥库 · HSM Custody</h4>
          <span className="sv-sub">
            {v.totalKeys} 密钥 · {v.apiKeys} API · {v.walletKeys} 钱包 · 30d 轮换 {v.rotated30d}
          </span>
        </div>
        <div className="sv-stats">
          <div className="sv-stat tone-green">
            <small>明文泄露</small>
            <strong>{v.plaintextLeaks}</strong>
          </div>
          <div className={v.expiringSoon > 0 ? 'sv-stat tone-yellow' : 'sv-stat tone-green'}>
            <small>临期</small>
            <strong>{v.expiringSoon}</strong>
          </div>
          <div className={v.expired > 0 ? 'sv-stat tone-red' : 'sv-stat tone-green'}>
            <small>过期</small>
            <strong>{v.expired}</strong>
          </div>
        </div>
      </div>

      <div className="sv-filter">
        <button className={filter === 'all' ? 'sv-tab active' : 'sv-tab'} onClick={() => setFilter('all')}>
          全部 <em>{keys.length}</em>
        </button>
        {(['api', 'wallet', 'ssh', 'webhook', 'db'] as TypeFilter[]).map((t) => (
          <button
            key={t}
            className={filter === t ? 'sv-tab active' : 'sv-tab'}
            onClick={() => setFilter(t)}
          >
            {TYPE_LABEL[t]} <em>{counts[t] || 0}</em>
          </button>
        ))}
      </div>

      <div className="sv-list">
        {list.map((k) => (
          <article className={`sv-row type-${k.typeTone} status-${k.statusTone}`} key={k.id}>
            <div className="sv-row-left">
              <span className={`sv-type tone-${k.typeTone}`}>{TYPE_ICON[k.type]}</span>
              <div className="sv-info">
                <div className="sv-info-head">
                  <strong>{k.label}</strong>
                  <em>{k.provider}</em>
                </div>
                <p className="sv-scope">{k.scope}</p>
              </div>
            </div>
            <div className="sv-row-meta">
              <div className="sv-meta-col">
                <small>轮换</small>
                <code>{k.rotated}</code>
              </div>
              <div className="sv-meta-col">
                <small>到期</small>
                <code>{k.expires}</code>
              </div>
              <div className="sv-meta-col">
                <small>剩余</small>
                <code className={k.daysToExpiry <= 14 ? 'warn' : k.daysToExpiry <= 30 ? 'watch' : ''}>
                  {k.daysToExpiry > 9000 ? '∞' : `${k.daysToExpiry}d`}
                </code>
              </div>
              <span className={`sv-status pill-${k.statusTone}`}>
                <i />
                {STATUS_LABEL[k.status]}
              </span>
            </div>
          </article>
        ))}
      </div>
    </div>
  )
}
