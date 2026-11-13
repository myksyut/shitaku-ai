import { Link, useParams } from 'react-router-dom'
import { Button, Card } from '../../components/ui'
import { AgendaEditor } from './AgendaEditor'
import { useGenerateAgenda, useOccurrence, useSeries } from './hooks'
import { OccurrenceKnowledgePanel } from './OccurrenceKnowledgePanel'
import { hasOccurrenceStarted } from './occurrence-time'
import { Badge, ErrorNotice, formatStart } from './SeriesUi'
import { calendarSyncErrorMessage, syncErrorMessage } from './sync-errors'
import { TopicList } from './TopicList'
import type { OccurrenceDetail, SeriesDetail } from './types'

function OccurrenceWorkspace({ series, detail }: { series: SeriesDetail; detail: OccurrenceDetail }) {
  const generate = useGenerateAgenda(series.id, detail.occurrence.id)
  const creator = series.role === 'creator'
  const sources = generate.data?.sources

  return (
    <div className="space-y-6 animate-fade-in">
      <Link to={`/series/${series.id}`} className="text-sm underline text-[var(--color-warm-gray-500)]">
        ← {series.title}
      </Link>
      <div className="space-y-2">
        <h1 className="text-2xl font-extrabold">{series.title}</h1>
        <p className="text-lg">{formatStart(detail.occurrence.start_at)}</p>
        <div className="flex gap-2">
          {detail.occurrence.is_cancelled && <Badge>キャンセル</Badge>}
          {detail.occurrence.needs_extraction && hasOccurrenceStarted(detail.occurrence.start_at) && (
            <Badge>未抽出</Badge>
          )}
        </div>
      </div>
      <TopicList seriesId={series.id} occurrence={detail.occurrence} topics={detail.topics} role={series.role} />
      <Card className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-xl font-bold">アジェンダ</h2>
          {creator && (
            <Button
              isLoading={generate.isPending}
              onClick={() => {
                if (!detail.agenda || window.confirm('アジェンダを再生成しますか？現在の編集内容は置き換えられます。'))
                  generate.mutate()
              }}
            >
              {detail.agenda ? 'アジェンダを再生成' : 'アジェンダを生成'}
            </Button>
          )}
        </div>
        {generate.isError && <ErrorNotice>アジェンダを生成できませんでした</ErrorNotice>}
        {sources && (
          <div className="space-y-2 text-sm">
            <p>
              参照: 議題{sources.topics}件 / 持ち越しアクション{sources.carried_action_items}件 / 論点
              {sources.open_issues}件 / 議事録{sources.knowledge}件 / Slack{sources.slack_messages}件
            </p>
            {sources.slack_error && <ErrorNotice>{syncErrorMessage('slack', sources.slack_error)}</ErrorNotice>}
            {sources.calendar_error && (
              <ErrorNotice>{calendarSyncErrorMessage(sources.calendar_error, series.role)}</ErrorNotice>
            )}
          </div>
        )}
        {detail.agenda ? (
          <AgendaEditor
            key={detail.agenda.updated_at}
            seriesId={series.id}
            agenda={detail.agenda}
            canEdit={creator && !generate.isPending}
          />
        ) : (
          <p className="text-sm text-[var(--color-warm-gray-500)]">
            {creator
              ? '投稿された議題やチームメモリから、この回のアジェンダを生成できます。'
              : 'アジェンダはまだ作成されていません'}
          </p>
        )}
      </Card>
      <OccurrenceKnowledgePanel
        seriesId={series.id}
        occurrenceId={detail.occurrence.id}
        startAt={detail.occurrence.start_at}
        role={series.role}
        knowledge={detail.knowledge}
        needsExtraction={detail.occurrence.needs_extraction}
      />
    </div>
  )
}

export function OccurrencePage() {
  const { seriesId = '', occurrenceId = '' } = useParams()
  const series = useSeries(seriesId)
  const occurrence = useOccurrence(seriesId, occurrenceId)
  if (series.isPending || occurrence.isPending) return <output>この回を読み込み中...</output>
  if (series.isError || occurrence.isError)
    return <ErrorNotice>この回が見つからないか、閲覧権限がありません</ErrorNotice>
  return <OccurrenceWorkspace key={`${seriesId}/${occurrenceId}`} series={series.data} detail={occurrence.data} />
}
