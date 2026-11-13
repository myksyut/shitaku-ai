import { useState } from 'react'
import { Button, Card, Input, Textarea } from '../../components/ui'
import { ApiError } from '../../lib/api-client'
import { useDeleteTopic, useSubmitTopic } from './hooks'
import { ErrorNotice } from './SeriesUi'
import type { AgendaTopic, OccurrenceSummary, SeriesRole } from './types'

export function TopicList({
  seriesId,
  occurrence,
  topics,
  role,
}: {
  seriesId: string
  occurrence: OccurrenceSummary
  topics: AgendaTopic[]
  role: SeriesRole
}) {
  const submit = useSubmitTopic(seriesId, occurrence.id)
  const remove = useDeleteTopic(seriesId, occurrence.id)
  const [title, setTitle] = useState('')
  const [details, setDetails] = useState('')
  const canSubmit = !occurrence.is_cancelled && new Date(occurrence.start_at).getTime() > Date.now()

  return (
    <Card className="space-y-4">
      <h2 className="text-xl font-bold">議題の投稿</h2>
      {topics.length === 0 ? (
        <p className="text-sm text-[var(--color-warm-gray-500)]">投稿された議題はありません</p>
      ) : (
        <ul className="divide-y divide-[var(--color-cream-300)]">
          {topics.map((topic) => (
            <li key={topic.id} className="space-y-2 py-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-bold">{topic.title}</h3>
                  <p className="text-xs text-[var(--color-warm-gray-500)]">{topic.author_label}</p>
                </div>
                {(topic.is_mine || role === 'creator') && (
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={remove.isPending}
                    aria-label={`${topic.title}を取り下げ`}
                    onClick={() => remove.mutate(topic.id)}
                  >
                    取り下げ
                  </Button>
                )}
              </div>
              {topic.details && <p className="whitespace-pre-wrap text-sm">{topic.details}</p>}
            </li>
          ))}
        </ul>
      )}
      {remove.isError && <ErrorNotice>議題を取り下げられませんでした</ErrorNotice>}
      {canSubmit ? (
        <form
          className="space-y-3 border-t border-[var(--color-cream-300)] pt-4"
          onSubmit={(event) => {
            event.preventDefault()
            if (title.trim())
              submit.mutate(
                { title: title.trim(), details: details.trim() || undefined },
                {
                  onSuccess: () => {
                    setTitle('')
                    setDetails('')
                  },
                },
              )
          }}
        >
          <Input
            id="topic-title"
            label="議題"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            required
            disabled={submit.isPending}
          />
          <Textarea
            id="topic-details"
            label="補足（任意）"
            value={details}
            onChange={(event) => setDetails(event.target.value)}
            rows={3}
            disabled={submit.isPending}
          />
          <Button type="submit" isLoading={submit.isPending} disabled={!title.trim()}>
            議題を投稿
          </Button>
        </form>
      ) : (
        <p className="text-sm text-[var(--color-warm-gray-500)]">
          {occurrence.is_cancelled
            ? 'キャンセルされた回には議題を投稿できません'
            : '開始済みの回には議題を投稿できません'}
        </p>
      )}
      {submit.isError && (
        <ErrorNotice>
          {submit.error instanceof ApiError && submit.error.status === 422
            ? '開始済み、またはキャンセルされた回には議題を投稿できません'
            : '議題を投稿できませんでした'}
        </ErrorNotice>
      )}
    </Card>
  )
}
