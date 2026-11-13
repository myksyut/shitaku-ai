import { Link } from 'react-router-dom'
import { Card } from '../../components/ui'
import { Badge, formatStart } from './SeriesUi'
import type { OccurrenceSummary } from './types'

export function OccurrenceList({ seriesId, occurrences }: { seriesId: string; occurrences: OccurrenceSummary[] }) {
  return (
    <section className="space-y-4">
      <h2 className="text-lg font-bold">回</h2>
      {occurrences.length === 0 ? (
        <p>同期された回がありません</p>
      ) : (
        <ol className="space-y-3">
          {occurrences.map((occurrence) => (
            <li key={occurrence.id}>
              <Card className="flex flex-wrap items-center justify-between gap-4">
                <div className="space-y-2">
                  <Link to={`/series/${seriesId}/occurrences/${occurrence.id}`} className="font-bold hover:underline">
                    {formatStart(occurrence.start_at)}
                  </Link>
                  <div className="flex flex-wrap gap-2">
                    {occurrence.is_cancelled && <Badge>キャンセル</Badge>}
                    {occurrence.has_agenda && <Badge>アジェンダあり</Badge>}
                    <Badge>議題{occurrence.topic_count}件</Badge>
                    <Badge>議事録{occurrence.knowledge_count}件</Badge>
                    {occurrence.needs_extraction && <Badge>未抽出</Badge>}
                  </div>
                </div>
                <Link
                  to={`/series/${seriesId}/occurrences/${occurrence.id}`}
                  className="text-sm font-semibold text-[var(--color-primary-700)] hover:underline"
                >
                  この回を開く →
                </Link>
              </Card>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
