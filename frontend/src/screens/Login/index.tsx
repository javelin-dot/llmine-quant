import { useState, useCallback } from 'react'
import { api, authStore } from '../../lib/api'

interface LoginProps {
  onSuccess: (userInfo: { userId: string; name: string; email: string }) => void
}

type Mode = 'login' | 'register'

export default function Login({ onSuccess }: LoginProps) {
  const [mode, setMode] = useState<Mode>('login')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const switchMode = useCallback((m: Mode) => {
    setMode(m)
    setError(null)
    setName('')
    setEmail('')
    setPassword('')
    setConfirmPassword('')
  }, [])

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      setError(null)

      if (mode === 'register') {
        if (!name.trim()) { setError('请填写姓名'); return }
        if (!email) { setError('请填写邮箱'); return }
        if (password.length < 6) { setError('密码至少 6 位'); return }
        if (password !== confirmPassword) { setError('两次密码不一致'); return }
        setLoading(true)
        try {
          const res = await api.auth.register(name.trim(), email, password)
          authStore.setToken(res.access_token)
          onSuccess({ userId: res.user_id, name: res.name, email: res.email })
        } catch (err) {
          const msg = err instanceof Error ? err.message : '注册失败'
          // surface conflict clearly
          setError(msg.includes('409') || msg.includes('already') ? '该邮箱已注册，请直接登录' : msg)
        } finally {
          setLoading(false)
        }
      } else {
        if (!email || !password) return
        setLoading(true)
        try {
          const res = await api.auth.login(email, password)
          authStore.setToken(res.access_token)
          onSuccess({ userId: res.user_id, name: res.name, email: res.email })
        } catch (err) {
          setError(err instanceof Error ? err.message : '登录失败')
        } finally {
          setLoading(false)
        }
      }
    },
    [mode, name, email, password, confirmPassword, onSuccess],
  )

  const isLoginReady = mode === 'login' && email && password
  const isRegisterReady = mode === 'register' && name && email && password && confirmPassword

  return (
    <div className="login-root">
      <div className="login-card">
        <div className="login-brand">
          <div className="logo" />
          <h1>LLMine Quant</h1>
          <span>AI-Native Quantitative Trading</span>
        </div>

        {/* Tab switcher */}
        <div className="login-tabs">
          <button
            type="button"
            className={`login-tab ${mode === 'login' ? 'active' : ''}`}
            onClick={() => switchMode('login')}
          >
            登录
          </button>
          <button
            type="button"
            className={`login-tab ${mode === 'register' ? 'active' : ''}`}
            onClick={() => switchMode('register')}
          >
            注册
          </button>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          {mode === 'register' && (
            <div className="login-field">
              <label htmlFor="reg-name">姓名</label>
              <input
                id="reg-name"
                type="text"
                autoComplete="name"
                placeholder="张三"
                value={name}
                onChange={e => setName(e.target.value)}
                disabled={loading}
              />
            </div>
          )}

          <div className="login-field">
            <label htmlFor="login-email">邮箱</label>
            <input
              id="login-email"
              type="email"
              autoComplete="email"
              placeholder={mode === 'login' ? 'admin@llmine.local' : 'you@example.com'}
              value={email}
              onChange={e => setEmail(e.target.value)}
              disabled={loading}
            />
          </div>

          <div className="login-field">
            <label htmlFor="login-password">密码</label>
            <input
              id="login-password"
              type="password"
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              placeholder={mode === 'register' ? '至少 6 位' : '••••••••'}
              value={password}
              onChange={e => setPassword(e.target.value)}
              disabled={loading}
            />
          </div>

          {mode === 'register' && (
            <div className="login-field">
              <label htmlFor="reg-confirm">确认密码</label>
              <input
                id="reg-confirm"
                type="password"
                autoComplete="new-password"
                placeholder="再次输入密码"
                value={confirmPassword}
                onChange={e => setConfirmPassword(e.target.value)}
                disabled={loading}
              />
            </div>
          )}

          {error && <div className="login-error">{error}</div>}

          <button
            className="btn login-submit"
            type="submit"
            disabled={loading || !(isLoginReady || isRegisterReady)}
          >
            {loading
              ? mode === 'login' ? '登录中…' : '注册中…'
              : mode === 'login' ? '登录' : '注册并登录'}
          </button>
        </form>

        {mode === 'login' && (
          <div className="login-hint">
            <span className="status-dot status-dot-blue" /> Dev账号：admin@llmine.local / admin123
          </div>
        )}
      </div>
    </div>
  )
}
