import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button, Card } from '../../components/ui'
import { CalendarEventPicker } from './CalendarEventPicker'
import { useMySeries } from './hooks'
import { Badge, ErrorNotice, formatStart } from './SeriesUi'
import { calendarSyncErrorMessage } from './sync-errors'

export function SeriesListPage() {
  const series = useMySeries()
  const [pickerOpen, setPickerOpen] = useState(false)

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold">わたしの定例</h1>
          <p className="mt-2 text-[var(--color-warm-gray-500)]">チームの記憶を、次の会議へ。</p>
        </div>
        <Button onClick={() => setPickerOpen(!pickerOpen)} aria-expanded={pickerOpen}>
          カレンダーから追加
        </Button>
      </div>
      {pickerOpen && <CalendarEventPicker />}
      {series.isPending ? (
        <output>定例を読み込み中...</output>
      ) : series.isError ? (
        <ErrorNotice>定例を読み込めませんでした</ErrorNotice>
      ) : series.data.length === 0 ? (
        <Card>
          <h2 className="text-lg font-bold">まだ定例がありません</h2>
          <p className="mt-2 text-[var(--color-warm-gray-500)]">
            カレンダーから追加して、参加者と議題やチームメモリを共有しましょう。
          </p>
        </Card>
      ) : (
        <div className="grid gap-5 md:grid-cols-2">
          {series.data.map((item) => (
            <Card key={item.id} className="space-y-4">
              <div className="flex items-start justify-between gap-3">
                <h2 className="text-xl font-bold">
                  <Link className="hover:underline" to={`/series/${item.id}`}>
                    {item.title}
                  </Link>
                </h2>
                <Badge>{item.role === 'creator' ? '作成者' : '参加者'}</Badge>
              </div>
              <p className="text-sm">
                {item.next_occurrence
                  ? `次回: ${formatStart(item.next_occurrence.start_at)}`
                  : '次回の予定はありません'}
              </p>
              <div className="flex flex-wrap gap-2">
                <Badge>未完了のアクション{item.open_action_items}件</Badge>
                {item.next_occurrence?.needs_extraction && <Badge>未抽出</Badge>}
              </div>
              {item.calendar_sync_error && (
                <ErrorNotice>{calendarSyncErrorMessage(item.calendar_sync_error, item.role)}</ErrorNotice>
              )}
              <Link className="font-semibold text-[var(--color-primary-700)] hover:underline" to={`/series/${item.id}`}>
                定例を開く →
              </Link>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
