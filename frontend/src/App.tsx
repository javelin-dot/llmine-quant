import { useState, useCallback, useEffect } from 'react'
import { api } from './lib/api'
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

type Screen = 'dashboard' | 'strategy' | 'backtest' | 'explain' | 'portfolio' | 'execution' | 'risk' | 'data' | 'security' | 'collaboration' | 'audit'
type ModalType = 'global' | 'kill' | 'create' | 'autopilot' | 'approve' | 'pause'

const VALID_SCREENS: Screen[] = ['dashboard', 'strategy', 'backtest', 'explain', 'portfolio', 'execution', 'risk', 'data', 'security', 'collaboration', 'audit']
const VALID_MODALS: ModalType[] = ['global', 'kill', 'create', 'autopilot', 'approve', 'pause']

const navItems: { target: Screen; icon: string; label: string }[] = [
  { target: 'dashboard', icon: '⌘', label: 'AI 指挥中心' },
  { target: 'strategy', icon: '◇', label: '策略工厂' },
  { target: 'backtest', icon: '↯', label: '回测实验室' },
  { target: 'explain', icon: '析', label: '解释与血缘' },
  { target: 'portfolio', icon: '◌', label: '组合驾驶舱' },
  { target: 'execution', icon: '⇄', label: '交易审批' },
]

const navControl: { target: Screen; icon: string; label: string }[] = [
  { target: 'risk', icon: '盾', label: '风控与熔断' },
  { target: 'data', icon: '源', label: '行情与合规' },
  { target: 'security', icon: '钥', label: '资金安全' },
  { target: 'collaboration', icon: '协', label: '协作实验室' },
  { target: 'audit', icon: '迹', label: '审计追踪' },
]

export default function App() {
  const [screen, setScreen] = useState<Screen>('dashboard')
  const [modal, setModal] = useState<ModalType | null>(null)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [globalData, setGlobalData] = useState<{
    meta: { product: string; subtitle: string }
    system: { healthScore: number; healthStatusLabel: string; healthBarHeights: number[]; autopilot: boolean; riskGateLabel: string }
    modals: Record<string, { title: string; body: string; primary: string }>
  } | null>(null)

  useEffect(() => {
    api.dashboard.overview()
      .then((d) => {
        setGlobalData({ meta: d.meta, system: d.system, modals: d.modals })
      })
      .catch((e) => console.error('Global API error:', e))
  }, [])

  const toggleSidebar = useCallback(() => setSidebarCollapsed((v) => !v), [])

  const switchScreen = useCallback((target: Screen) => {
    setScreen(target)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [])

  const openModal = useCallback((type: ModalType) => setModal(type), [])
  const closeModal = useCallback(() => setModal(null), [])

  const handleScreenNavigate = useCallback((target: string) => {
    if ((VALID_SCREENS as string[]).includes(target)) {
      switchScreen(target as Screen)
    }
  }, [switchScreen])

  const handleScreenModal = useCallback((target: string) => {
    if ((VALID_MODALS as string[]).includes(target)) {
      openModal(target as ModalType)
    }
  }, [openModal])

  const modalData = modal && globalData ? globalData.modals[modal] : null

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
              className={screen === n.target ? 'nav-btn active' : 'nav-btn'}
              onClick={() => switchScreen(n.target)}
            >
              <span className="nav-ico">{n.icon}</span>
              <span>{n.label}</span>
            </button>
          ))}
        </nav>

        <div className="nav-section-title">Control</div>
        <nav className="nav" aria-label="控制导航">
          {navControl.map((n) => (
            <button
              key={n.target}
              className={screen === n.target ? 'nav-btn active' : 'nav-btn'}
              onClick={() => switchScreen(n.target)}
            >
              <span className="nav-ico">{n.icon}</span>
              <span>{n.label}</span>
            </button>
          ))}
        </nav>

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
      </aside>

      {/* Main */}
      <main>
        {/* Topbar */}
        <header className="topbar">
          <div className="search">
            <span>⌕</span>
            <input
              placeholder="告诉 AI：例如‘生成一个 BTC/ETH 激进趋势策略，最大回撤 20%，自动完成回测和模拟盘部署’"
              onKeyDown={(e) => { if (e.key === 'Enter') openModal('create') }}
            />
          </div>
          <div className="top-actions">
            <span className="pill">
              <span className="dot" /> AI Autopilot {globalData?.system.autopilot ? 'ON' : 'OFF'}
            </span>
            <span className="pill">{globalData?.system.riskGateLabel ?? '—'}</span>
            <button className="btn secondary" onClick={() => openModal('global')}>全局概览</button>
            <button className="btn danger" onClick={() => openModal('kill')}>Kill Switch</button>
          </div>
        </header>

        {/* ===== Dashboard ===== */}
        <section className={screen === 'dashboard' ? 'screen active' : 'screen'}>
          <Dashboard onNavigate={handleScreenNavigate} onModal={handleScreenModal} />
        </section>

        {/* ===== Strategy ===== */}
        <section className={screen === 'strategy' ? 'screen active' : 'screen'}>
          <Strategy onNavigate={handleScreenNavigate} onModal={handleScreenModal} />
        </section>

        {/* ===== Backtest ===== */}
        <section className={screen === 'backtest' ? 'screen active' : 'screen'}>
          <Backtest onNavigate={handleScreenNavigate} onModal={handleScreenModal} />
        </section>

        {/* ===== Explain ===== */}
        <section className={screen === 'explain' ? 'screen active' : 'screen'}>
          <Explain onNavigate={handleScreenNavigate} onModal={handleScreenModal} />
        </section>

        {/* ===== Portfolio ===== */}
        <section className={screen === 'portfolio' ? 'screen active' : 'screen'}>
          <Portfolio onNavigate={handleScreenNavigate} onModal={handleScreenModal} />
        </section>

        {/* ===== Execution ===== */}
        <section className={screen === 'execution' ? 'screen active' : 'screen'}>
          <Execution onNavigate={handleScreenNavigate} onModal={handleScreenModal} />
        </section>

        {/* ===== Risk ===== */}
        <section className={screen === 'risk' ? 'screen active' : 'screen'}>
          <Risk onNavigate={handleScreenNavigate} onModal={handleScreenModal} />
        </section>

        {/* ===== Data ===== */}
        <section className={screen === 'data' ? 'screen active' : 'screen'}>
          <Data onNavigate={handleScreenNavigate} onModal={handleScreenModal} />
        </section>

        {/* ===== Security ===== */}
        <section className={screen === 'security' ? 'screen active' : 'screen'}>
          <Security onNavigate={handleScreenNavigate} onModal={handleScreenModal} />
        </section>
        {/* ===== Collaboration ===== */}
        <section className={screen === 'collaboration' ? 'screen active' : 'screen'}>
          <Collaboration onNavigate={handleScreenNavigate} onModal={handleScreenModal} />
        </section>

        {/* ===== Audit ===== */}
        <section className={screen === 'audit' ? 'screen active' : 'screen'}>
          <Audit onNavigate={handleScreenNavigate} onModal={handleScreenModal} />
        </section>
      </main>

      {/* Mobile Tabs */}
      <div className="mobile-tabs">
        {['dashboard', 'strategy', 'backtest', 'explain', 'execution', 'risk'].map((t) => (
          <button
            key={t}
            className={screen === t ? 'nav-btn active' : 'nav-btn'}
            onClick={() => switchScreen(t as Screen)}
          >
            {navItems.find((n) => n.target === t)?.icon || navControl.find((n) => n.target === t)?.icon}
          </button>
        ))}
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
