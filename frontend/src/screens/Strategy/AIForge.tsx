import { useState } from 'react'
import { useStrategy } from '../../contexts/StrategyContext'

const RISK_FILTERS: { id: 'all' | 'conservative' | 'balanced' | 'aggressive'; label: string; tone: string }[] = [
  { id: 'all', label: '全部', tone: 'blue' },
  { id: 'conservative', label: '保守', tone: 'green' },
  { id: 'balanced', label: '平衡', tone: 'yellow' },
  { id: 'aggressive', label: '激进', tone: 'red' },
]

interface AIForgeProps {
  onModal?: (target: string) => void
}

export default function AIForge({ onModal }: AIForgeProps) {
  const data = useStrategy()
  const [prompt, setPrompt] = useState(data.nlPrompt)
  const [risk, setRisk] = useState<'all' | 'conservative' | 'balanced' | 'aggressive'>('all')
  const [activeTemplate, setActiveTemplate] = useState<string | null>(null)

  const filteredTemplates = data.templates.filter((t) =>
    risk === 'all' ? true : t.risk === risk
  )

  return (
    <div className="ai-forge">
      <div className="ai-forge-left">
        <div className="ai-forge-head">
          <div>
            <span className="ai-forge-eyebrow">
              <span className="ai-forge-eyebrow-dot" />
              AI Strategy Forge · 一句话生成可回测策略
            </span>
            <h2 className="ai-forge-title">告诉 AI 你的目标</h2>
          </div>
          <div className="ai-forge-shortcut">
            <kbd>⌘</kbd>
            <kbd>K</kbd>
          </div>
        </div>

        <div className="ai-forge-prompt">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            spellCheck={false}
            placeholder="例如：创建一个 BTC 趋势突破策略，最大回撤 15%，自动完成回测和模拟盘部署"
          />
          <div className="ai-forge-prompt-foot">
            <span className="ai-forge-counter">{prompt.length} 字符 · 7 个候选生成</span>
            <div className="ai-forge-actions">
              <button className="btn secondary">保存为模板</button>
              <button
                className="btn ai-forge-cta"
                onClick={() => onModal?.('create')}
              >
                <span>✦</span> 让 Agent 开始
              </button>
            </div>
          </div>
        </div>

        <div className="ai-forge-filters">
          <span className="ai-forge-filter-label">风险偏好</span>
          {RISK_FILTERS.map((f) => (
            <button
              key={f.id}
              className={`ai-forge-chip chip-${f.tone} ${risk === f.id ? 'active' : ''}`}
              onClick={() => setRisk(f.id)}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div className="ai-forge-templates">
          {filteredTemplates.map((t) => {
            const tone =
              t.risk === 'conservative' ? 'green' : t.risk === 'balanced' ? 'yellow' : 'red'
            return (
              <button
                key={t.id}
                className={`ai-forge-template tpl-${tone} ${activeTemplate === t.id ? 'active' : ''}`}
                onClick={() => setActiveTemplate(t.id)}
              >
                <div className="ai-forge-template-top">
                  <span className={`ai-forge-template-tag tag-${tone}`}>{
                    t.risk === 'conservative' ? '保守' : t.risk === 'balanced' ? '平衡' : '激进'
                  }</span>
                  <span className="ai-forge-template-family">{t.family}</span>
                </div>
                <strong className="ai-forge-template-name">{t.name}</strong>
                <p className="ai-forge-template-desc">{t.desc}</p>
                <span className="ai-forge-template-market">{t.market}</span>
              </button>
            )
          })}
        </div>
      </div>

      <div className="ai-forge-right">
        <div className="ai-forge-feed-head">
          <div>
            <h4 className="ai-forge-feed-title">
              <span className="ai-forge-feed-pulse" />
              Live Generation Feed
            </h4>
            <span className="ai-forge-feed-sub">Agent 决策追踪 · 实时</span>
          </div>
          <span className="ai-forge-feed-count">{data.feed.length}</span>
        </div>
        <div className="ai-forge-feed">
          {data.feed.map((f, i) => (
            <div className={`ai-forge-feed-item feed-${f.tone}`} key={i}>
              <div className="ai-forge-feed-time">{f.time}</div>
              <div className="ai-forge-feed-body">
                <span className="ai-forge-feed-agent">{f.agent}</span>
                <p className="ai-forge-feed-event">{f.event}</p>
              </div>
              <span className={`ai-forge-feed-dot dot-${f.tone}`} />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
