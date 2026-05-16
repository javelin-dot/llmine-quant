import { useState } from 'react'
import { api, type MarketDataImportSummary } from '../../lib/api'

const PRESET_GROUPS: { label: string; symbols: string[] }[] = [
  { label: '大盘蓝筹', symbols: ['600519.SH', '601318.SH', '601398.SH', '600036.SH', '600900.SH'] },
  { label: '新能源 / 半导体', symbols: ['300750.SZ', '688981.SH', '600438.SH', '688008.SH'] },
  { label: '消费 / 医药', symbols: ['000333.SZ', '000858.SZ', '600276.SH', '603259.SH'] },
  { label: '互联网 / 科技', symbols: ['300059.SZ', '002415.SZ', '300760.SZ', '300015.SZ'] },
]

function isoDaysAgo(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() - days)
  return d.toISOString().slice(0, 10)
}

function todayISO(): string {
  return new Date().toISOString().slice(0, 10)
}

interface Props {
  onImported?: () => void
}

export default function MarketDataImporter({ onImported }: Props) {
  const [expanded, setExpanded] = useState(false)
  const [symbolsText, setSymbolsText] = useState('600519.SH\n300750.SZ\n000001.SZ')
  const [startDate, setStartDate] = useState(isoDaysAgo(365 * 3))
  const [endDate, setEndDate] = useState(todayISO())
  const [adjust, setAdjust] = useState<'qfq' | 'hfq' | 'none'>('qfq')
  const [importing, setImporting] = useState(false)
  const [summary, setSummary] = useState<MarketDataImportSummary | null>(null)
  const [error, setError] = useState<string | null>(null)

  const parsedSymbols = symbolsText
    .split(/[\s,;]+/)
    .map((s) => s.trim().toUpperCase())
    .filter((s) => s.length > 0)

  const addPreset = (syms: string[]) => {
    const existing = new Set(parsedSymbols)
    const merged = [...parsedSymbols, ...syms.filter((s) => !existing.has(s))]
    setSymbolsText(merged.join('\n'))
  }

  const submit = async () => {
    if (!parsedSymbols.length) { setError('请至少填写一个标的代码'); return }
    if (!startDate || !endDate) { setError('请选择起止日期'); return }
    if (startDate > endDate) { setError('起止日期顺序有误'); return }
    setImporting(true); setError(null); setSummary(null)
    try {
      const result = await api.data.importAkshare({
        symbols: parsedSymbols,
        start_date: startDate,
        end_date: endDate,
        adjust,
      })
      setSummary(result)
      if (result.errors.length === 0 && result.importedRows > 0) {
        onImported?.()
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setImporting(false)
    }
  }

  return (
    <section className="data-importer">
      <button className="data-importer-toggle" onClick={() => setExpanded((v) => !v)}>
        <span className="data-importer-toggle-icon">{expanded ? '▼' : '▸'}</span>
        <span className="data-importer-toggle-title">导入日线行情（AKShare）</span>
        <span className="data-importer-toggle-hint">
          {expanded ? '点击收起' : '本地无数据时来这里——这是回测实验室"三步选股"的数据源'}
        </span>
      </button>

      {expanded && (
        <div className="data-importer-body">
          <div className="data-importer-row">
            <label className="data-importer-label">
              标的代码
              <span className="data-importer-sub">每行一个，或用逗号/分号分隔；后缀 .SH / .SZ / .BJ</span>
            </label>
            <textarea
              className="data-importer-textarea"
              value={symbolsText}
              onChange={(e) => setSymbolsText(e.target.value)}
              rows={5}
              placeholder="600519.SH&#10;300750.SZ&#10;000001.SZ"
            />
            <div className="data-importer-presets">
              <span className="data-importer-presets-label">快速添加：</span>
              {PRESET_GROUPS.map((g) => (
                <button
                  key={g.label}
                  className="bt-chip-btn"
                  onClick={() => addPreset(g.symbols)}
                  title={g.symbols.join(', ')}
                >＋ {g.label}</button>
              ))}
              <button className="bt-chip-btn" onClick={() => setSymbolsText('')}>清空</button>
              <span className="data-importer-count">
                共 <strong>{parsedSymbols.length}</strong> 只
              </span>
            </div>
          </div>

          <div className="data-importer-row data-importer-row-grid">
            <label className="data-importer-field">
              <span>起始日期</span>
              <input type="date" className="bt-input" value={startDate}
                     onChange={(e) => setStartDate(e.target.value)} />
            </label>
            <label className="data-importer-field">
              <span>截止日期</span>
              <input type="date" className="bt-input" value={endDate}
                     onChange={(e) => setEndDate(e.target.value)} />
            </label>
            <label className="data-importer-field">
              <span>复权方式</span>
              <select className="bt-input" value={adjust}
                      onChange={(e) => setAdjust(e.target.value as 'qfq' | 'hfq' | 'none')}>
                <option value="qfq">前复权（推荐）</option>
                <option value="hfq">后复权</option>
                <option value="none">不复权</option>
              </select>
            </label>
          </div>

          <div className="data-importer-actions">
            <button
              className="bt-btn bt-btn-primary"
              disabled={importing || parsedSymbols.length === 0}
              onClick={() => void submit()}
            >
              {importing ? <><span className="bt-spinner" /> 导入中（{parsedSymbols.length} 只）…</> : `▶ 导入 ${parsedSymbols.length} 只`}
            </button>
            <span className="data-importer-hint-inline">
              导入耗时约 1-3 秒 / 标的；导入完成后可立即在「回测实验室 → Agent 构建」中使用
            </span>
          </div>

          {error && <div className="bt-toast bt-toast-red">{error}</div>}

          {summary && (
            <div className={`data-importer-summary ${summary.errors.length ? 'has-errors' : ''}`}>
              <div className="data-importer-summary-row">
                <span className="data-importer-summary-stat">
                  <span className="label">导入总行数</span>
                  <span className="value">{summary.importedRows}</span>
                </span>
                <span className="data-importer-summary-stat">
                  <span className="label">新增</span>
                  <span className="value pos">{summary.insertedRows}</span>
                </span>
                <span className="data-importer-summary-stat">
                  <span className="label">更新</span>
                  <span className="value">{summary.updatedRows}</span>
                </span>
                <span className="data-importer-summary-stat">
                  <span className="label">跳过</span>
                  <span className="value">{summary.skippedRows}</span>
                </span>
                <span className="data-importer-summary-stat">
                  <span className="label">覆盖范围</span>
                  <span className="value">{summary.startDate ?? '—'} ~ {summary.endDate ?? '—'}</span>
                </span>
                <span className="data-importer-summary-stat">
                  <span className="label">成功标的</span>
                  <span className="value">{summary.symbols.length} 只</span>
                </span>
              </div>
              {summary.errors.length > 0 && (
                <div className="data-importer-errors">
                  <strong>失败明细 ({summary.errors.length})：</strong>
                  <ul>
                    {summary.errors.slice(0, 10).map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                    {summary.errors.length > 10 && <li>… 还有 {summary.errors.length - 10} 条</li>}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  )
}
