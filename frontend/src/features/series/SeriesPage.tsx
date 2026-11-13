import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Button } from '../../components/ui'
import { DictionarySection } from '../dictionary/DictionarySection'
import { AttendeeList } from './AttendeeList'
import { useSeries } from './hooks'
import { MemoryBoard } from './MemoryBoard'
import { OccurrenceList } from './OccurrenceList'
import { SeriesSettingsPanel } from './SeriesSettingsPanel'
import { Badge, ErrorNotice } from './SeriesUi'
import { calendarSyncErrorMessage } from './sync-errors'
import type { SeriesDetail } from './types'

function SeriesWorkspace({ series }: { series: SeriesDetail }) {
  const [selected, setSelected] = useState('回')
  const tab = selected === '設定' && series.role !== 'creator' ? '回' : selected
  const tabs = series.role === 'creator' ? ['回', 'チームメモリ', '辞書', '設定'] : ['回', 'チームメモリ', '辞書']

  return (
    <div className="space-y-6 animate-fade-in">
      <Link to="/" className="text-sm underline text-[var(--color-warm-gray-500)]">
        ← わたしの定例
      </Link>
      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-extrabold">{series.title}</h1>
          <Badge>{series.role === 'creator' ? '作成者' : '参加者'}</Badge>
        </div>
        {series.settings.description && (
          <p className="whitespace-pre-wrap text-[var(--color-warm-gray-600)]">{series.settings.description}</p>
        )}
        {series.slack && (
          <p className="text-sm text-[var(--color-warm-gray-500)]">
            参照するSlack: {series.slack.channels.map((channel) => `#${channel.name}`).join('、') || 'チャンネル未選択'}
          </p>
        )}
      </div>
      {series.calendar.error && (
        <ErrorNotice>{calendarSyncErrorMessage(series.calendar.error, series.role)}</ErrorNotice>
      )}
      <nav aria-label="定例のメニュー" className="flex flex-wrap gap-2 border-b border-[var(--color-cream-300)] pb-3">
        {tabs.map((label) => (
          <Button
            key={label}
            variant={tab === label ? 'secondary' : 'ghost'}
            aria-pressed={tab === label}
            onClick={() => setSelected(label)}
          >
            {label}
          </Button>
        ))}
      </nav>
      {tab === '回' && <OccurrenceList seriesId={series.id} occurrences={series.occurrences} />}
      {tab === 'チームメモリ' && (
        <MemoryBoard seriesId={series.id} role={series.role} occurrences={series.occurrences} />
      )}
      {tab === '辞書' && <DictionarySection seriesId={series.id} seriesRole={series.role} />}
      {tab === '設定' && series.role === 'creator' && <SeriesSettingsPanel series={series} />}
      <AttendeeList attendees={series.attendees} />
    </div>
  )
}

export function SeriesPage() {
  const { seriesId = '' } = useParams()
  const series = useSeries(seriesId)
  if (series.isPending) return <output>定例を読み込み中...</output>
  if (series.isError) return <ErrorNotice>定例が見つからないか、閲覧権限がありません</ErrorNotice>
  return <SeriesWorkspace key={series.data.id} series={series.data} />
}
