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

export default function Data({ onModal }: DataProps) {
  const [data, setData] = useState<MockData['data'] | null>(null)
  const [libRefresh, setLibRefresh] = useState(0)

  const refresh = useCallback(() => {
    api.data.overview()
      .then(setData)
      .catch((e) => console.error('Data API error:', e))
  }, [])

  useEffect(() => { refresh() }, [refresh])

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
        <MarketSyncButton onChanged={onSyncChanged} />
        <MarketDataImporter onImported={onImported} />
        <LocalMarketLibrary refreshKey={libRefresh} />
        <div className="data-main">
          <SourceMatrix />
          <LatencyTimeline />
        </div>
        <LineageGraph />
        <div className="data-sub">
          <IncidentTimeline />
        </div>
      </div>
    </DataProvider>
  )
}
