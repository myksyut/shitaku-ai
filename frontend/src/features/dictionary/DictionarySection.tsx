import { useState } from 'react'
import { Button, Card } from '../../components/ui'
import { ErrorNotice } from '../series/SeriesUi'
import type { SeriesRole } from '../series/types'
import { DictionaryEntryForm } from './DictionaryEntryForm'
import { useDeleteDictionaryEntry, useDictionaryEntries } from './hooks'
import { CATEGORY_LABELS, type DictionaryEntry } from './types'

export function DictionarySection({ seriesId, seriesRole }: { seriesId: string; seriesRole: SeriesRole }) {
  const entries = useDictionaryEntries(seriesId)
  const deleteEntry = useDeleteDictionaryEntry(seriesId)
  const [form, setForm] = useState<{ entry: DictionaryEntry | null } | null>(null)

  if (entries.isPending) return <output>辞書を読み込み中...</output>
  if (entries.isError) return <ErrorNotice>辞書を読み込めませんでした</ErrorNotice>

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-lg font-bold">辞書</h2>
        {seriesRole === 'creator' && (
          <Button variant="secondary" onClick={() => setForm({ entry: null })}>
            辞書を追加
          </Button>
        )}
      </div>
      {deleteEntry.isError && <ErrorNotice>辞書エントリを削除できませんでした</ErrorNotice>}
      {entries.data.length === 0 ? (
        <p>辞書エントリがありません</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {entries.data.map((entry) => (
            <Card key={entry.id} className="space-y-2">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-bold">{entry.canonical_name}</h3>
                  {entry.category && (
                    <span className="text-xs text-[var(--color-warm-gray-500)]">{CATEGORY_LABELS[entry.category]}</span>
                  )}
                </div>
                {seriesRole === 'creator' && (
                  <div className="flex gap-2">
                    <Button variant="ghost" size="sm" onClick={() => setForm({ entry })}>
                      編集
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={deleteEntry.isPending}
                      onClick={() => {
                        if (window.confirm('この辞書エントリを削除しますか？')) deleteEntry.mutate(entry.id)
                      }}
                    >
                      削除
                    </Button>
                  </div>
                )}
              </div>
              {entry.aliases.length > 0 && <p className="text-sm">表記揺れ: {entry.aliases.join('、')}</p>}
              {entry.description && <p className="text-sm text-[var(--color-warm-gray-600)]">{entry.description}</p>}
            </Card>
          ))}
        </div>
      )}
      {seriesRole === 'creator' && form && (
        <DictionaryEntryForm seriesId={seriesId} entry={form.entry} onClose={() => setForm(null)} />
      )}
    </section>
  )
}
