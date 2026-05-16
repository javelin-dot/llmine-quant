import { useCallback, useEffect, useState } from 'react'
import { api } from '../../lib/api'
import type { MockData } from '../../data/types'
import { DataProvider } from '../../contexts/DataContext'
import DataHeader from './DataHeader'
import MarketSyncButton from './MarketSyncButton'
import MarketDataImporter from './MarketDataImporter'
import LocalMarketLibrary from './LocalMarketLibrary'
import SourceMatrix from './SourceMatrix'
import LatencyTimeline from './LatencyTimeline'
import LineageGraph from './LineageGraph'
import IncidentTimeline from './IncidentTimeline'

interface DataProps {
  onNavigate?: (target: string) => void
  onModal?: (target: string) => void
}

type DataTabId = 'overview' | 'ingest' | 'sources' | 'lineage' | 'incidents'

const TAB_DEFS: { id: DataTabId; label: string }[] = [
  { id: 'overview', label: '可靠性概览' },
  { id: 'ingest', label: '行情入库' },
  { id: 'sources', label: '数据源·趋势' },
  { id: 'lineage', label: '血缘' },
  { id: 'incidents', label: '事件' },
]

export default function Data({ onModal }: DataProps) {
  const [data, setData] = useState<MockData['data'] | null>(null)
  const [libRefresh, setLibRefresh] = useState(0)
  const [tab, setTab] = useState<DataTabId>('overview')

  const refresh = useCallback(() => {
    api.data
      .overview()
      .then(setData)
      .catch((e) => console.error('Data API error:', e))
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const onImported = useCallback(() => {
    refresh()
    setLibRefresh((v) => v + 1)
  }, [refresh])

  const onSyncChanged = useCallback(() => {
    setLibRefresh((v) => v + 1)
  }, [])

  if (!data) return <div className="data-root">Loading Data…</div>

  return (
    <DataProvider value={data}>
      <div className="data-root">
        <DataHeader onModal={onModal} />
        <nav className="data-tabs-bar" aria-label="数据控制台分区">
          {TAB_DEFS.map((row) => (
            <button
              key={row.id}
              type="button"
              className={`data-tab-btn${tab === row.id ? ' active' : ''}`}
              onClick={() => setTab(row.id)}
            >
              {row.label}
            </button>
          ))}
        </nav>

        <div className="data-tab-stage">
          {tab === 'overview' && (
            <p className="data-tab-hint">上方 KPI 与健康度为全盘聚合；切换到「行情入库」管理本地 OHLCV 与同步。</p>
          )}

          {tab === 'ingest' && (
            <div className="data-ingest-stack">
              <MarketSyncButton onChanged={onSyncChanged} />
              <MarketDataImporter onImported={onImported} />
              <LocalMarketLibrary refreshKey={libRefresh} />
            </div>
          )}

          {tab === 'sources' && (
            <div className="data-main">
              <SourceMatrix />
              <LatencyTimeline />
            </div>
          )}

          {tab === 'lineage' && <LineageGraph />}

          {tab === 'incidents' && (
            <div className="data-sub data-sub-single">
              <IncidentTimeline />
            </div>
          )}
        </div>
      </div>
    </DataProvider>
  )
}
