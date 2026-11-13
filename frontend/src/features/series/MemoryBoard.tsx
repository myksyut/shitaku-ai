import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button, Card } from '../../components/ui'
import { useDeleteMemoryItem, useSetResolution, useTeamMemory } from './hooks'
import { MEMORY_LABELS, MemoryItemForm } from './MemoryItemForm'
import { Badge, ErrorNotice, formatStart } from './SeriesUi'
import type { MemoryItem, OccurrenceSummary, SeriesRole } from './types'

const RESOLUTION_LABELS = { reversed: '撤回済み', done: '完了', dropped: '取り下げ', resolved: '解決済み' }

export function MemoryBoard({
  seriesId,
  role,
  occurrences,
}: {
  seriesId: string
  role: SeriesRole
  occurrences: OccurrenceSummary[]
}) {
  const memory = useTeamMemory(seriesId)
  const resolution = useSetResolution(seriesId)
  const remove = useDeleteMemoryItem(seriesId)
  const [form, setForm] = useState<{ item: MemoryItem | null } | null>(null)
  const pending = resolution.isPending || remove.isPending

  if (memory.isPending) return <output>チームメモリを読み込み中...</output>
  if (memory.isError) return <ErrorNotice>チームメモリを読み込めませんでした</ErrorNotice>

  return (
    <section className="space-y-5">
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-lg font-bold">チームメモリ</h2>
        {role === 'creator' && (
          <Button variant="secondary" onClick={() => setForm({ item: null })}>
            メモリを追加
          </Button>
        )}
      </div>
      {(resolution.isError || remove.isError) && (
        <ErrorNotice>メモリを更新できませんでした。変更は保存されていません</ErrorNotice>
      )}
      {(['decision', 'action_item', 'open_issue'] as const).map((kind) => (
        <Card key={kind} className="space-y-3">
          <h3 className="font-bold">{MEMORY_LABELS[kind]}</h3>
          {memory.data.items.filter((item) => item.kind === kind).length === 0 && (
            <p className="text-sm text-[var(--color-warm-gray-500)]">まだありません</p>
          )}
          <ul className="divide-y divide-[var(--color-cream-300)]">
            {memory.data.items
              .filter((item) => item.kind === kind)
              .map((item) => (
                <li key={item.id} className="space-y-3 py-3">
                  <div className="flex items-start gap-3">
                    {item.kind === 'action_item' && (
                      <input
                        type="checkbox"
                        aria-label={`${item.body}を完了`}
                        className="mt-1 size-5 accent-[var(--color-primary-500)]"
                        checked={item.resolution === 'done'}
                        disabled={pending}
                        onChange={(event) =>
                          resolution.mutate({ itemId: item.id, resolution: event.target.checked ? 'done' : null })
                        }
                      />
                    )}
                    <div className="min-w-0 flex-1 space-y-2">
                      <p
                        className={`whitespace-pre-wrap break-words ${item.resolution ? 'text-[var(--color-warm-gray-500)]' : ''}`}
                      >
                        {item.body}
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {item.resolution && <Badge>{RESOLUTION_LABELS[item.resolution]}</Badge>}
                        {'carry_over' in item && item.carry_over > 0 && <Badge>{item.carry_over}回持ち越し</Badge>}
                        {item.extracted && <Badge>議事録から抽出</Badge>}
                      </div>
                      {item.kind === 'action_item' && (
                        <p className="text-sm text-[var(--color-warm-gray-600)]">
                          担当: {item.assignee_email ?? '未定'}
                          {item.due_on && ` / 期限: ${item.due_on}`}
                        </p>
                      )}
                      <Link
                        to={`/series/${seriesId}/occurrences/${item.origin_occurrence_id}`}
                        className="text-xs underline text-[var(--color-warm-gray-500)]"
                      >
                        起点: {formatStart(item.origin_start_at)}
                      </Link>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {item.kind === 'action_item' && (
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={pending}
                        onClick={() =>
                          resolution.mutate({ itemId: item.id, resolution: item.resolution ? null : 'dropped' })
                        }
                      >
                        {item.resolution ? '再オープン' : '取り下げ'}
                      </Button>
                    )}
                    {role === 'creator' && (
                      <>
                        {item.kind === 'decision' && (
                          <Button
                            variant="ghost"
                            size="sm"
                            disabled={pending}
                            onClick={() =>
                              resolution.mutate({ itemId: item.id, resolution: item.resolution ? null : 'reversed' })
                            }
                          >
                            {item.resolution ? '決定を戻す' : '決定を撤回'}
                          </Button>
                        )}
                        {item.kind === 'open_issue' && (
                          <>
                            <Button
                              variant="ghost"
                              size="sm"
                              disabled={pending}
                              onClick={() =>
                                resolution.mutate({ itemId: item.id, resolution: item.resolution ? null : 'resolved' })
                              }
                            >
                              {item.resolution ? '再オープン' : '解決'}
                            </Button>
                            {!item.resolution && (
                              <Button
                                variant="ghost"
                                size="sm"
                                disabled={pending}
                                onClick={() => resolution.mutate({ itemId: item.id, resolution: 'dropped' })}
                              >
                                取り下げ
                              </Button>
                            )}
                          </>
                        )}
                        <Button variant="ghost" size="sm" disabled={pending} onClick={() => setForm({ item })}>
                          編集
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={pending}
                          onClick={() => {
                            if (window.confirm('このメモリを削除しますか？')) remove.mutate(item.id)
                          }}
                        >
                          削除
                        </Button>
                      </>
                    )}
                  </div>
                </li>
              ))}
          </ul>
        </Card>
      ))}
      {role === 'creator' && form && (
        <MemoryItemForm seriesId={seriesId} occurrences={occurrences} item={form.item} onClose={() => setForm(null)} />
      )}
    </section>
  )
}
