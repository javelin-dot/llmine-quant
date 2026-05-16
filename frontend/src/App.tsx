import { useState, useCallback, useEffect } from 'react'
import { api, authStore } from './lib/api'
import { strategyWs, executionWs, riskWs } from './lib/ws'
import Login from './screens/Login'
import Dashboard from './screens/Dashboard'
import Strategy from './screens/Strategy'
import Backtest from './screens/Backtest'
import Explain from './screens/Explain'
import Portfolio from './screens/Portfolio'
import Execution from './screens/Execution'
import Risk from './screens/Risk'
import Data from './screens/Data'
import Security from './screens/Security'
import Collaboration from './screens/Collaboration'
import Audit from './screens/Audit'
import Paper from './screens/Paper'
import Agent from './screens/Agent'

type Screen = 'dashboard' | 'agent' | 'strategy' | 'backtest' | 'explain' | 'portfolio' | 'execution' | 'risk' | 'data' | 'security' | 'collaboration' | 'audit' | 'paper'
type ModalType = 'global' | 'kill' | 'create' | 'autopilot' | 'approve' | 'pause'

const VALID_SCREENS: Screen[] = ['dashboard', 'agent', 'strategy', 'backtest', 'explain', 'portfolio', 'execution', 'risk', 'data', 'security', 'collaboration', 'audit', 'paper']
const VALID_MODALS: ModalType[] = ['global', 'kill', 'create', 'autopilot', 'approve', 'pause']

type NavEntry = { target: Screen; label: string; abbr: string }

const navItems: NavEntry[] = [
  { target: 'dashboard', label: 'Dashboard', abbr: '主页' },
  { target: 'agent', label: 'Agent', abbr: 'Agent' },
  { target: 'strategy', label: '策略工厂', abbr: '策略' },
  { target: 'backtest', label: '回测实验室', abbr: '回测' },
  { target: 'paper', label: '模拟盘', abbr: '模拟' },
  { target: 'explain', label: '解释与血缘', abbr: '解释' },
  { target: 'portfolio', label: '组合驾驶舱', abbr: '组合' },
  { target: 'execution', label: '交易审批', abbr: '审批' },
]

const navControl: NavEntry[] = [
  { target: 'risk', label: '风控与熔断', abbr: '风控' },
  { target: 'data', label: '行情数据', abbr: '行情' },
  { target: 'security', label: '资金安全', abbr: '资金' },
  { target: 'collaboration', label: '协作实验室', abbr: '协作' },
  { target: 'audit', label: '审计追踪', abbr: '审计' },
]

const NAV_MOBILE_ORDER: Screen[] = ['dashboard', 'agent', 'strategy', 'backtest', 'explain', 'execution', 'risk']

const navLookup: NavEntry[] = [...navItems, ...navControl]

export default function App() {
  const [screen, setScreen] = useState<Screen>('dashboard')
  const [modal, setModal] = useState<ModalType | null>(null)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [backtestContext, setBacktestContext] = useState<{ strategyId?: string; taskId?: string }>({})
  const [paperContext, setPaperContext] = useState<{ accountId?: string }>({})
  const [currentUser, setCurrentUser] = useState<{ userId: string; name: string; email: string } | null>(null)
  const [authChecked, setAuthChecked] = useState(false)
  const [globalData, setGlobalData] = useState<{
    meta: { product: string; subtitle: string }
    system: { healthScore: number; healthStatusLabel: string; healthBarHeights: number[]; autopilot: boolean; riskGateLabel: string }
    modals: Record<string, { title: string; body: string; primary: string }>
  } | null>(null)

  // Restore session from localStorage on mount
  useEffect(() => {
    if (authStore.isAuthenticated()) {
      api.auth.me().then(u => {
        if (u) setCurrentUser({ userId: u.user_id, name: u.name, email: u.email })
        else authStore.clearToken()
        setAuthChecked(true)
      }).catch(() => { authStore.clearToken(); setAuthChecked(true) })
    } else {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setAuthChecked(true)
    }
  }, [])

  // Listen for 401 events from api.ts
  useEffect(() => {
    const handler = () => { setCurrentUser(null); authStore.clearToken() }
    window.addEventListener('llmine:unauthorized', handler)
    return () => window.removeEventListener('llmine:unauthorized', handler)
  }, [])

  useEffect(() => {
    if (!currentUser) return
    api.dashboard.overview()
      .then((d) => {
        setGlobalData({ meta: d.meta, system: d.system, modals: d.modals })
      })
      .catch((e) => console.error('Global API error:', e))
  }, [currentUser])

  // WebSocket connections — start when authenticated, stop on logout
  useEffect(() => {
    if (!currentUser) return
    strategyWs.connect()
    executionWs.connect()
    riskWs.connect()
    return () => {
      strategyWs.disconnect()
      executionWs.disconnect()
      riskWs.disconnect()
    }
  }, [currentUser])

  const toggleSidebar = useCallback(() => setSidebarCollapsed((v) => !v), [])

  const switchScreen = useCallback((target: Screen) => {
    setScreen(target)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [])

  const openModal = useCallback((type: ModalType) => setModal(type), [])
  const closeModal = useCallback(() => setModal(null), [])

  const handleScreenNavigate = useCallback((target: string) => {
    // Support compound targets like `backtest:strategyId=abc`, `backtest:taskId=xyz`,
    // or `paper:accountId=abc`.
    const [base, rest] = target.split(':')
    if ((VALID_SCREENS as string[]).includes(base)) {
      if (base === 'backtest') {
        if (rest) {
          const ctx: { strategyId?: string; taskId?: string } = {}
          for (const piece of rest.split('&')) {
            const [k, v] = piece.split('=')
            if (k === 'strategyId' && v) ctx.strategyId = decodeURIComponent(v)
            if (k === 'taskId' && v) ctx.taskId = decodeURIComponent(v)
          }
          setBacktestContext(ctx)
        } else {
          setBacktestContext({})
        }
      } else if (base === 'paper') {
        if (rest) {
          const ctx: { accountId?: string } = {}
          for (const piece of rest.split('&')) {
            const [k, v] = piece.split('=')
            if (k === 'accountId' && v) ctx.accountId = decodeURIComponent(v)
          }
          setPaperContext(ctx)
        } else {
          setPaperContext({})
        }
      }
      switchScreen(base as Screen)
    }
  }, [switchScreen])

  const handleScreenModal = useCallback((target: string) => {
    if ((VALID_MODALS as string[]).includes(target)) {
      openModal(target as ModalType)
    }
  }, [openModal])

  const modalData = modal && globalData ? globalData.modals[modal] : null

  const renderActiveScreen = () => {
    switch (screen) {
      case 'dashboard':
        return <Dashboard onNavigate={handleScreenNavigate} onModal={handleScreenModal} />
      case 'agent':
        return <Agent onNavigate={handleScreenNavigate} onModal={handleScreenModal} />
      case 'strategy':
        return <Strategy onNavigate={handleScreenNavigate} onModal={handleScreenModal} />
      case 'backtest':
        return (
          <Backtest
            onNavigate={handleScreenNavigate}
            onModal={handleScreenModal}
            initialStrategyId={backtestContext.strategyId}
            initialTaskId={backtestContext.taskId}
          />
        )
      case 'explain':
        return <Explain onNavigate={handleScreenNavigate} onModal={handleScreenModal} />
      case 'portfolio':
        return <Portfolio onNavigate={handleScreenNavigate} onModal={handleScreenModal} />
      case 'execution':
        return <Execution onNavigate={handleScreenNavigate} onModal={handleScreenModal} />
      case 'risk':
        return <Risk onNavigate={handleScreenNavigate} onModal={handleScreenModal} />
      case 'data':
        return <Data onNavigate={handleScreenNavigate} onModal={handleScreenModal} />
      case 'security':
        return <Security onNavigate={handleScreenNavigate} onModal={handleScreenModal} />
      case 'collaboration':
        return <Collaboration onNavigate={handleScreenNavigate} onModal={handleScreenModal} />
      case 'audit':
        return <Audit onNavigate={handleScreenNavigate} onModal={handleScreenModal} />
      case 'paper':
        return <Paper onNavigate={handleScreenNavigate} onModal={handleScreenModal} initialAccountId={paperContext.accountId} />
      default:
        return null
    }
  }

  if (!authChecked) return null

  if (!currentUser) {
    return <Login onSuccess={u => setCurrentUser(u)} />
  }

  return (
    <div className={`app ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
      {/* Sidebar */}
      <aside className={`sidebar ${sidebarCollapsed ? 'collapsed' : ''}`}>
        <button className="sidebar-toggle" onClick={toggleSidebar} aria-label={sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'}>
          {sidebarCollapsed ? '▸' : '◂'}
        </button>
        <div className="brand">
          <div className="logo" />
          <div>
            <h1>{globalData?.meta.product ?? 'LLMine Quant'}</h1>
            <span>{globalData?.meta.subtitle ?? ''}</span>
          </div>
        </div>

        <div className="nav-section-title">Command</div>
        <nav className="nav" aria-label="主导航">
          {navItems.map((n) => (
            <button
              key={n.target}
              type="button"
              className={screen === n.target ? 'nav-btn active' : 'nav-btn'}
              title={n.label}
              onClick={() => switchScreen(n.target)}
            >
              <span className="nav-label">{n.label}</span>
              <span className="nav-abbr">{n.abbr}</span>
            </button>
          ))}
        </nav>

        <div className="nav-section-title">Control</div>
        <nav className="nav" aria-label="控制导航">
          {navControl.map((n) => (
            <button
              key={n.target}
              type="button"
              className={screen === n.target ? 'nav-btn active' : 'nav-btn'}
              title={n.label}
              onClick={() => switchScreen(n.target)}
            >
              <span className="nav-label">{n.label}</span>
              <span className="nav-abbr">{n.abbr}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="side-card">
            <div className="label">System Health</div>
            <div className="score">
              <strong>{globalData?.system.healthScore ?? '—'}</strong>
              <span>{globalData?.system.healthStatusLabel ?? '—'}</span>
            </div>
            <div className="mini-bars" aria-hidden="true">
              {(globalData?.system.healthBarHeights ?? []).map((h, i) => (
                <i key={i} style={{ height: `${h}px` }} />
              ))}
            </div>
          </div>

          <div className="session-card" aria-label="会话">
            <span className="session-user" title={currentUser.email}>
              <span className="session-user-dot" aria-hidden="true" />
              <span className="session-user-copy">
                <strong>{currentUser.name}</strong>
                <small>{currentUser.email}</small>
              </span>
            </span>
            <button
              type="button"
              className="btn secondary session-logout"
              onClick={async () => {
                const token = authStore.getToken()
                if (token) await api.auth.logout(token).catch(() => {})
                authStore.clearToken()
                setCurrentUser(null)
              }}
            >
              退出
            </button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main>
        <header className="mobile-session-bar" aria-label="会话">
          <span className="session-user" title={currentUser.email}>
            <span className="session-user-dot" aria-hidden="true" />
            <span className="session-user-copy">
              <strong>{currentUser.name}</strong>
              <small>{currentUser.email}</small>
            </span>
          </span>
          <button
            type="button"
            className="btn secondary session-logout"
            onClick={async () => {
              const token = authStore.getToken()
              if (token) await api.auth.logout(token).catch(() => {})
              authStore.clearToken()
              setCurrentUser(null)
            }}
          >
            退出
          </button>
        </header>

        <section className="screen active">{renderActiveScreen()}</section>
      </main>

      {/* Mobile Tabs */}
      <div className="mobile-tabs">
        {NAV_MOBILE_ORDER.map((t) => {
          const entry = navLookup.find((n) => n.target === t)
          return (
            <button
              key={t}
              type="button"
              className={screen === t ? 'nav-btn active' : 'nav-btn'}
              title={entry?.label ?? t}
              onClick={() => switchScreen(t)}
            >
              <span className="mobile-tab-abbr">{entry?.abbr ?? t}</span>
            </button>
          )
        })}
      </div>

      {/* Modal */}
      {modal && modalData && (
        <div className="modal-backdrop show" role="dialog" aria-modal="true" onClick={(e) => { if (e.target === e.currentTarget) closeModal() }}>
          <div className="modal">
            <div className="modal-body">
              <h3>{modalData.title}</h3>
              <p>{modalData.body}</p>
            </div>
            <div className="modal-actions">
              <button className="btn secondary" onClick={closeModal}>关闭</button>
              <button className="btn" onClick={closeModal}>{modalData.primary}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
