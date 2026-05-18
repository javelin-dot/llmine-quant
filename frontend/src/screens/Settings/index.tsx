import { useCallback, useEffect, useState } from 'react'
import { api, type AdminRoleRow, type AdminUserRow } from '../../lib/api'

type SettingsTab = 'account' | 'ai' | 'users'

const AI_PROVIDERS = [
  { id: 'anthropic', name: 'Anthropic Claude', path: 'claude-sonnet-4-6', status: 'active', isDefault: true },
  { id: 'openai', name: 'OpenAI GPT', path: 'gpt-4o', status: 'active', isDefault: false },
]

const ROLE_LABEL: Record<string, string> = {
  admin: '管理员',
  researcher: '研究员',
  trader: '交易员',
  risk_officer: '风控',
  viewer: '只读',
}

function formatRoles(roles: string[]) {
  return roles.map((r) => ROLE_LABEL[r] ?? r).join('、') || '—'
}

interface Props {
  onClose: () => void
  currentUser: { userId: string; name: string; email: string; roles: string[] }
  system: { healthScore: number; healthStatusLabel: string; healthBarHeights: number[] } | null
  onLogout: () => void | Promise<void>
  canManageUsers: boolean
}

export default function Settings({ onClose, currentUser, system, onLogout, canManageUsers }: Props) {
  const [tab, setTab] = useState<SettingsTab>('account')
  const [proxy, setProxy] = useState('')
  const [proxySaved, setProxySaved] = useState(false)

  const [users, setUsers] = useState<AdminUserRow[]>([])
  const [roles, setRoles] = useState<AdminRoleRow[]>([])
  const [usersLoading, setUsersLoading] = useState(false)
  const [usersErr, setUsersErr] = useState<string | null>(null)

  const [inviteOpen, setInviteOpen] = useState(false)
  const [inviteName, setInviteName] = useState('')
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState('researcher')
  const [invitePassword, setInvitePassword] = useState('')
  const [inviteSaving, setInviteSaving] = useState(false)
  const [inviteErr, setInviteErr] = useState<string | null>(null)
  const [inviteResult, setInviteResult] = useState<{ initial_password: string; email: string } | null>(null)

  const [editUser, setEditUser] = useState<AdminUserRow | null>(null)
  const [editName, setEditName] = useState('')
  const [editStatus, setEditStatus] = useState<'active' | 'inactive'>('active')
  const [editSaving, setEditSaving] = useState(false)
  const [editErr, setEditErr] = useState<string | null>(null)

  useEffect(() => {
    if (!canManageUsers && tab === 'users') setTab('account')
  }, [canManageUsers, tab])

  const reloadUsers = useCallback(async () => {
    setUsersLoading(true)
    setUsersErr(null)
    try {
      const [uRows, rRows] = await Promise.all([api.auth.listUsers(), api.auth.listRoles()])
      setUsers(uRows)
      setRoles(rRows)
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      setUsersErr(msg)
    } finally {
      setUsersLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!canManageUsers || tab !== 'users') return
    void reloadUsers()
  }, [canManageUsers, tab, reloadUsers])

  useEffect(() => {
    if (!inviteOpen || roles.length === 0) return
    setInviteRole((cur) => (roles.some((r) => r.name === cur) ? cur : roles[0].name))
  }, [inviteOpen, roles])

  useEffect(() => {
    if (!inviteOpen || !canManageUsers) return
    if (roles.length > 0) return
    void api.auth.listRoles().then(setRoles).catch(() => {})
  }, [inviteOpen, canManageUsers, roles.length])

  function openAgentStudio() {
    window.open(window.location.origin + window.location.pathname + '#agent-studio', '_blank')
  }

  function saveProxy() {
    setProxySaved(true)
    setTimeout(() => setProxySaved(false), 2000)
  }

  async function submitInvite(e: React.FormEvent) {
    e.preventDefault()
    setInviteErr(null)
    setInviteSaving(true)
    try {
      const payload: { name: string; email: string; role_name: string; password?: string } = {
        name: inviteName.trim(),
        email: inviteEmail.trim(),
        role_name: inviteRole,
      }
      const pw = invitePassword.trim()
      if (pw) payload.password = pw
      const res = await api.auth.inviteUser(payload)
      setInviteResult({ initial_password: res.initial_password, email: res.email })
      setInviteName('')
      setInviteEmail('')
      setInvitePassword('')
      await reloadUsers()
    } catch (err) {
      setInviteErr(err instanceof Error ? err.message : '邀请失败')
    } finally {
      setInviteSaving(false)
    }
  }

  function openEdit(u: AdminUserRow) {
    setEditUser(u)
    setEditName(u.name)
    setEditStatus(u.status === 'inactive' ? 'inactive' : 'active')
    setEditErr(null)
  }

  async function submitEdit(e: React.FormEvent) {
    e.preventDefault()
    if (!editUser) return
    setEditSaving(true)
    setEditErr(null)
    try {
      const body: { name?: string; status?: string } = {}
      const trimmed = editName.trim()
      if (trimmed !== editUser.name) body.name = trimmed
      if (editStatus !== editUser.status) body.status = editStatus
      if (Object.keys(body).length === 0) {
        setEditUser(null)
        return
      }
      const updated = await api.auth.updateUser(editUser.user_id, body)
      setUsers((prev) => prev.map((u) => (u.user_id === updated.user_id ? updated : u)))
      setEditUser(null)
    } catch (err) {
      setEditErr(err instanceof Error ? err.message : '保存失败')
    } finally {
      setEditSaving(false)
    }
  }

  return (
    <div className="settings-overlay" onClick={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div className="settings-panel" onClick={(e) => e.stopPropagation()}>
        <div className="settings-header">
          <h2>设置</h2>
          <button type="button" className="settings-close" onClick={onClose} aria-label="关闭">✕</button>
        </div>

        <div className="settings-tabs">
          <button type="button" className={tab === 'account' ? 'active' : ''} onClick={() => setTab('account')}>
            账户与安全
          </button>
          <button type="button" className={tab === 'ai' ? 'active' : ''} onClick={() => setTab('ai')}>
            AI 管理
          </button>
          {canManageUsers && (
            <button type="button" className={tab === 'users' ? 'active' : ''} onClick={() => setTab('users')}>
              用户管理
            </button>
          )}
        </div>

        <div className="settings-body">
          {tab === 'account' && (
            <div className="settings-overview">
              <div className="settings-overview-card settings-overview-account">
                <div className="settings-overview-card-head">
                  <h3>当前账户</h3>
                  <span className="settings-overview-muted">会话</span>
                </div>
                <span className="session-user settings-overview-session" title={currentUser.email}>
                  <span className="session-user-dot" aria-hidden="true" />
                  <span className="session-user-copy">
                    <strong>{currentUser.name}</strong>
                    <small>{currentUser.email}</small>
                  </span>
                </span>
                {currentUser.roles.length > 0 && (
                  <p className="settings-account-roles">角色 · {formatRoles(currentUser.roles)}</p>
                )}
                <button
                  type="button"
                  className="settings-logout-btn"
                  onClick={async () => {
                    await onLogout()
                    onClose()
                  }}
                >
                  <span aria-hidden className="settings-logout-icon">⎋</span>
                  退出登录
                </button>
              </div>

              <div className="settings-overview-card settings-health-card">
                <div className="settings-overview-card-head">
                  <h3>系统状态</h3>
                  <span className="settings-health-pill">{system?.healthStatusLabel ?? '—'}</span>
                </div>
                <div className="settings-health-score">
                  <strong>{system?.healthScore ?? '—'}</strong>
                  <span className="settings-health-label">健康度</span>
                </div>
                <div className="mini-bars mini-bars-settings" aria-hidden="true">
                  {(system?.healthBarHeights ?? []).map((h, i) => (
                    <i key={i} style={{ height: `${h}px` }} />
                  ))}
                </div>
              </div>
            </div>
          )}

          {tab === 'ai' && (
            <>
              <div className="settings-section">
                <div className="settings-section-head">
                  <h3>AI 供应商</h3>
                  <button type="button" className="btn" style={{ fontSize: 13 }}>+ 添加</button>
                </div>
                <div className="settings-provider-list">
                  {AI_PROVIDERS.map((p) => (
                    <div key={p.id} className={`settings-provider-row ${p.isDefault ? 'default' : ''}`}>
                      <span className="settings-provider-dot" data-status={p.status} />
                      <div className="settings-provider-info">
                        <strong>{p.name}</strong>
                        <small>{p.path}</small>
                      </div>
                      {p.isDefault && <span className="settings-tag-default">默认</span>}
                      <div className="settings-provider-actions">
                        <button type="button" className="btn secondary" style={{ fontSize: 12, padding: '5px 12px' }}>测试</button>
                        {!p.isDefault && (
                          <button type="button" className="settings-remove-btn" aria-label="删除">✕</button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="settings-section">
                <div className="settings-section-head">
                  <h3>Agent 编排</h3>
                </div>
                <div className="settings-agent-shortcut">
                  <div>
                    <strong>Agent Studio</strong>
                    <p>在独立窗口中定义 Agent、编排工作流、调试运行链路。</p>
                  </div>
                  <button type="button" className="btn" onClick={openAgentStudio}>
                    打开 Agent Studio ↗
                  </button>
                </div>
              </div>

              <div className="settings-section">
                <div className="settings-section-head">
                  <h3>网络代理</h3>
                </div>
                <div className="settings-proxy-row">
                  <div className="settings-proxy-label">代理地址（留空则直连）</div>
                  <div className="settings-proxy-input-row">
                    <input
                      className="settings-input"
                      placeholder="http://127.0.0.1:7890"
                      value={proxy}
                      onChange={(e) => setProxy(e.target.value)}
                    />
                    <button type="button" className="btn" onClick={saveProxy}>
                      {proxySaved ? '已保存 ✓' : '保存'}
                    </button>
                  </div>
                </div>
              </div>
            </>
          )}

          {canManageUsers && tab === 'users' && (
            <div className="settings-users-wrap">
              <div className="settings-section settings-users-section">
                <div className="settings-section-head">
                  <h3>用户列表</h3>
                  <button type="button" className="btn" style={{ fontSize: 13 }} onClick={() => {
                    setInviteOpen(true)
                    setInviteErr(null)
                    setInviteResult(null)
                  }}>
                    + 邀请用户
                  </button>
                </div>
                {usersLoading && <p className="settings-muted">加载中…</p>}
                {usersErr && <p className="settings-users-err">{usersErr}</p>}
                {!usersLoading && !usersErr && (
                  <div className="settings-user-table">
                    <div className="settings-user-thead">
                      <span>姓名</span>
                      <span>邮箱</span>
                      <span>角色</span>
                      <span>状态</span>
                      <span />
                    </div>
                    {users.map((u) => (
                      <div key={u.user_id} className="settings-user-row">
                        <span className="settings-user-name">
                          <span className={`status-dot-${u.status === 'active' ? 'green' : 'gray'}`} />
                          {u.name}
                        </span>
                        <span className="settings-user-email">{u.email}</span>
                        <span className="settings-user-role-cell">{formatRoles(u.roles)}</span>
                        <span>
                          <span className={`status-tag-${u.status === 'active' ? 'green' : 'gray'}`}>
                            {u.status === 'active' ? '启用' : '禁用'}
                          </span>
                        </span>
                        <span className="settings-user-actions">
                          <button type="button" className="btn secondary" style={{ fontSize: 12, padding: '4px 10px' }} onClick={() => openEdit(u)}>
                            编辑
                          </button>
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {inviteOpen && (
          <div className="settings-submodal-backdrop" role="presentation" onClick={() => !inviteSaving && setInviteOpen(false)}>
            <div className="settings-submodal" role="dialog" aria-modal="true" aria-labelledby="invite-title" onClick={(e) => e.stopPropagation()}>
              <div className="settings-submodal-head">
                <h4 id="invite-title">邀请用户</h4>
                <button type="button" className="settings-close" aria-label="关闭" disabled={inviteSaving} onClick={() => setInviteOpen(false)}>✕</button>
              </div>
              {inviteResult ? (
                <div className="settings-invite-done">
                  <p>已向 <strong>{inviteResult.email}</strong> 创建账号。</p>
                  <p className="settings-muted">请将初始密码（仅显示一次）安全告知对方：</p>
                  <div className="settings-password-box">
                    <code>{inviteResult.initial_password}</code>
                    <button type="button" className="btn secondary" style={{ fontSize: 12 }} onClick={() => void navigator.clipboard.writeText(inviteResult.initial_password)}>复制</button>
                  </div>
                  <button type="button" className="btn" style={{ marginTop: 14 }} onClick={() => { setInviteResult(null); setInviteOpen(false) }}>
                    完成
                  </button>
                </div>
              ) : (
                <form className="settings-invite-form" onSubmit={submitInvite}>
                  {inviteErr && <p className="settings-users-err">{inviteErr}</p>}
                  <label className="settings-field">
                    <span>姓名</span>
                    <input className="settings-input" required value={inviteName} onChange={(e) => setInviteName(e.target.value)} />
                  </label>
                  <label className="settings-field">
                    <span>邮箱</span>
                    <input className="settings-input" type="email" required value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} />
                  </label>
                  <label className="settings-field">
                    <span>角色</span>
                    <select className="settings-input" value={inviteRole} onChange={(e) => setInviteRole(e.target.value)}>
                      {roles.map((r) => (
                        <option key={r.id} value={r.name}>{ROLE_LABEL[r.name] ?? r.name}</option>
                      ))}
                    </select>
                  </label>
                  <label className="settings-field">
                    <span>初始密码（可选，留空则自动生成）</span>
                    <input
                      className="settings-input"
                      type="password"
                      autoComplete="new-password"
                      placeholder="至少 8 位"
                      value={invitePassword}
                      onChange={(e) => setInvitePassword(e.target.value)}
                    />
                  </label>
                  <div className="settings-submodal-actions">
                    <button type="button" className="btn secondary" disabled={inviteSaving} onClick={() => setInviteOpen(false)}>取消</button>
                    <button type="submit" className="btn" disabled={inviteSaving}>{inviteSaving ? '创建中…' : '创建'}</button>
                  </div>
                </form>
              )}
            </div>
          </div>
        )}

        {editUser && (
          <div className="settings-submodal-backdrop" role="presentation" onClick={() => !editSaving && setEditUser(null)}>
            <div className="settings-submodal" role="dialog" aria-modal="true" aria-labelledby="edit-user-title" onClick={(e) => e.stopPropagation()}>
              <div className="settings-submodal-head">
                <h4 id="edit-user-title">编辑用户</h4>
                <button type="button" className="settings-close" aria-label="关闭" disabled={editSaving} onClick={() => setEditUser(null)}>✕</button>
              </div>
              <form className="settings-invite-form" onSubmit={submitEdit}>
                {editErr && <p className="settings-users-err">{editErr}</p>}
                <p className="settings-muted mono">{editUser.email}</p>
                <label className="settings-field">
                  <span>姓名</span>
                  <input className="settings-input" required value={editName} onChange={(e) => setEditName(e.target.value)} />
                </label>
                <label className="settings-field">
                  <span>状态</span>
                  <select className="settings-input" value={editStatus} onChange={(e) => setEditStatus(e.target.value === 'inactive' ? 'inactive' : 'active')}>
                    <option value="active">启用</option>
                    <option value="inactive">禁用</option>
                  </select>
                </label>
                <div className="settings-submodal-actions">
                  <button type="button" className="btn secondary" disabled={editSaving} onClick={() => setEditUser(null)}>取消</button>
                  <button type="submit" className="btn" disabled={editSaving}>{editSaving ? '保存中…' : '保存'}</button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
