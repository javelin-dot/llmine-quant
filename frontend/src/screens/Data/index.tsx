import { useEffect, useState } from 'react'
import { api } from '../../lib/api'
import type { MockData } from '../../data/types'
import { DataProvider } from '../../contexts/DataContext'
import DataHeader from './DataHeader'
import SourceMatrix from './SourceMatrix'
import LatencyTimeline from './LatencyTimeline'
import LineageGraph from './LineageGraph'
import BiasGate from './BiasGate'
import IncidentTimeline from './IncidentTimeline'

interface DataProps {
  onNavigate?: (target: string) => void
  onModal?: (target: string) => void
}

export default function Data({ onModal }: DataProps) {
  const [data, setData] = useState<MockData['data'] | null>(null)

  useEffect(() => {
    api.data.overview()
      .then(setData)
      .catch((e) => console.error('Data API error:', e))
  }, [])

  if (!data) return <div className="data-root">Loading Data…</div>

  return (
    <DataProvider value={data}>
      <div className="data-root">
        <DataHeader onModal={onModal} />
        <div className="data-main">
          <SourceMatrix />
          <LatencyTimeline />
        </div>
        <LineageGraph />
        <div className="data-sub">
          <BiasGate />
          <IncidentTimeline />
        </div>
      </div>
    </DataProvider>
  )
}
