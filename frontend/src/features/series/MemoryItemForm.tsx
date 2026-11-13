import { useState } from 'react'
import { Button, Input, Modal, Textarea } from '../../components/ui'
import { useCreateMemoryItem, useEditMemoryItem } from './hooks'
import { ErrorNotice, formatStart } from './SeriesUi'
import type { MemoryItem, NewMemoryRequest, OccurrenceSummary } from './types'

export const MEMORY_LABELS = { decision: '決定事項', action_item: 'アクションアイテム', open_issue: '未解決の論点' }

export function MemoryItemForm({
  seriesId,
  occurrences,
  item,
  onClose,
}: {
  seriesId: string
  occurrences: OccurrenceSummary[]
  item: MemoryItem | null
  onClose: () => void
}) {
  const create = useCreateMemoryItem(seriesId)
  const edit = useEditMemoryItem(seriesId)
  const [kind, setKind] = useState<MemoryItem['kind']>(item?.kind ?? 'decision')
  const [body, setBody] = useState(item?.body ?? '')
  const [origin, setOrigin] = useState(item?.origin_occurrence_id ?? '')
  const [assignee, setAssignee] = useState(item?.kind === 'action_item' ? (item.assignee_email ?? '') : '')
  const [dueOn, setDueOn] = useState(item?.kind === 'action_item' ? (item.due_on ?? '') : '')
  const pending = create.isPending || edit.isPending

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    const common = { body: body.trim(), origin_occurrence_id: origin }
    const request: NewMemoryRequest =
      kind === 'action_item'
        ? { ...common, kind, assignee_email: assignee.trim() || null, due_on: dueOn || null }
        : { ...common, kind }
    try {
      if (item) await edit.mutateAsync({ itemId: item.id, request })
      else await create.mutateAsync(request)
      onClose()
    } catch {
      return
    }
  }

  return (
    <Modal isOpen onClose={onClose} title={item ? 'メモリを編集' : 'メモリを追加'}>
      <form onSubmit={submit} className="space-y-4">
        <div>
          <label htmlFor="memory-kind" className="label">
            種類
          </label>
          <select
            id="memory-kind"
            className="input"
            value={kind}
            disabled={!!item || pending}
            onChange={(event) => {
              const value = event.target.value
              if (value === 'decision' || value === 'action_item' || value === 'open_issue') setKind(value)
            }}
          >
            {Object.entries(MEMORY_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <Textarea
          id="memory-body"
          label="内容"
          value={body}
          onChange={(event) => setBody(event.target.value)}
          required
          rows={4}
          disabled={pending}
        />
        <div>
          <label htmlFor="memory-origin" className="label">
            起点の回
          </label>
          <select
            id="memory-origin"
            className="input"
            value={origin}
            onChange={(event) => setOrigin(event.target.value)}
            required
            disabled={pending}
          >
            <option value="">回を選択してください</option>
            {occurrences.map((occurrence) => (
              <option key={occurrence.id} value={occurrence.id}>
                {formatStart(occurrence.start_at)}
                {occurrence.is_cancelled ? '（キャンセル）' : ''}
              </option>
            ))}
          </select>
        </div>
        {kind === 'action_item' && (
          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              id="memory-assignee"
              label="担当者のメールアドレス"
              type="email"
              value={assignee}
              onChange={(event) => setAssignee(event.target.value)}
              disabled={pending}
            />
            <Input
              id="memory-due"
              label="期限"
              type="date"
              value={dueOn}
              onChange={(event) => setDueOn(event.target.value)}
              disabled={pending}
            />
          </div>
        )}
        {(create.isError || edit.isError) && <ErrorNotice>メモリを保存できませんでした</ErrorNotice>}
        <div className="flex justify-end gap-3">
          <Button type="button" variant="ghost" onClick={onClose} disabled={pending}>
            キャンセル
          </Button>
          <Button type="submit" isLoading={pending} disabled={!body.trim() || !origin}>
            保存
          </Button>
        </div>
      </form>
    </Modal>
  )
}
