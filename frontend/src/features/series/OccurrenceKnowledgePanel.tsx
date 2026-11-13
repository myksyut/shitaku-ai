import { useState } from 'react'
import { Button, Card } from '../../components/ui'
import { useAddKnowledge, useDeleteKnowledge, useExtractMemory, useTranscriptCandidates } from './hooks'
import { KnowledgeDetail } from './KnowledgeDetail'
import { KnowledgeUpload } from './KnowledgeUpload'
import { hasOccurrenceStarted } from './occurrence-time'
import { Badge, ErrorNotice, formatStart } from './SeriesUi'
import type { AddKnowledgeResponse, KnowledgeSummary, SeriesRole } from './types'

export function OccurrenceKnowledgePanel({
  seriesId,
  occurrenceId,
  startAt,
  role,
  knowledge,
  needsExtraction,
}: {
  seriesId: string
  occurrenceId: string
  startAt: string
  role: SeriesRole
  knowledge: KnowledgeSummary[]
  needsExtraction: boolean
}) {
  const [uploadOpen, setUploadOpen] = useState(false)
  const [candidatesOpen, setCandidatesOpen] = useState(false)
  const [selected, setSelected] = useState<string | null>(null)
  const [added, setAdded] = useState<AddKnowledgeResponse | null>(null)
  const add = useAddKnowledge(seriesId, occurrenceId)
  const remove = useDeleteKnowledge(seriesId, occurrenceId)
  const extract = useExtractMemory(seriesId, occurrenceId)
  const candidates = useTranscriptCandidates(seriesId, occurrenceId, role === 'creator' && candidatesOpen)
  const pending = add.isPending || extract.isPending || remove.isPending
  const started = hasOccurrenceStarted(startAt)

  function afterAdded(result: AddKnowledgeResponse) {
    setAdded(result)
    setUploadOpen(false)
    setCandidatesOpen(false)
    if (hasOccurrenceStarted(startAt)) extract.mutate()
  }

  return (
    <Card className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl font-bold">議事録・ナレッジ {needsExtraction && started && <Badge>未抽出</Badge>}</h2>
        {role === 'creator' && (
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              disabled={pending}
              onClick={() => {
                add.reset()
                setUploadOpen(true)
              }}
            >
              テキストを追加
            </Button>
            <Button
              variant="secondary"
              disabled={pending}
              aria-expanded={candidatesOpen}
              onClick={() => {
                add.reset()
                setCandidatesOpen(!candidatesOpen)
              }}
            >
              Meetから追加
            </Button>
          </div>
        )}
      </div>
      {knowledge.length === 0 ? (
        <p className="text-sm text-[var(--color-warm-gray-500)]">議事録・ナレッジはまだありません</p>
      ) : (
        <ul className="divide-y divide-[var(--color-cream-300)]">
          {knowledge.map((item) => (
            <li key={item.id} className="space-y-2 py-3">
              <div className="flex items-start justify-between gap-3">
                <Button variant="ghost" className="text-left" onClick={() => setSelected(item.id)}>
                  {item.title ?? (item.source === 'meet_transcript' ? 'Meetトランスクリプト' : 'アップロード議事録')}
                </Button>
                {role === 'creator' && (
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={pending}
                    aria-label={`${item.title ?? '議事録'}を削除`}
                    onClick={() => {
                      if (window.confirm('この議事録・ナレッジを削除しますか？'))
                        remove.mutate(item.id, {
                          onSuccess: () => {
                            if (selected === item.id) setSelected(null)
                          },
                        })
                    }}
                  >
                    削除
                  </Button>
                )}
              </div>
              <p className="text-xs text-[var(--color-warm-gray-500)]">{formatStart(item.created_at)}</p>
              <p className="whitespace-pre-wrap text-sm text-[var(--color-warm-gray-600)]">{item.excerpt}</p>
            </li>
          ))}
        </ul>
      )}
      {role === 'creator' && (
        <>
          {candidatesOpen && (
            <section className="space-y-3 rounded-xl bg-[var(--color-cream-100)] p-4">
              <h3 className="font-bold">Meetトランスクリプトの候補</h3>
              {candidates.isPending ? (
                <output>候補を読み込み中...</output>
              ) : candidates.isError ? (
                <ErrorNotice>
                  候補を取得できませんでした。GoogleのDrive・ドキュメントの権限を確認してください
                </ErrorNotice>
              ) : candidates.data.length === 0 ? (
                <p>この回の候補はありません</p>
              ) : (
                <ul className="space-y-2">
                  {candidates.data.map((candidate) => (
                    <li key={candidate.google_doc_id} className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <p className="font-semibold">{candidate.name}</p>
                        <p className="text-xs">{formatStart(candidate.created_at)}</p>
                      </div>
                      <Button
                        disabled={pending}
                        onClick={() =>
                          add.mutate(
                            { source: 'meet_transcript', google_doc_id: candidate.google_doc_id },
                            { onSuccess: afterAdded },
                          )
                        }
                      >
                        {started ? '選択して抽出' : '選択して追加'}
                      </Button>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )}
          {added && (
            <div className="space-y-2 text-sm">
              <p>議事録を追加しました。{added.replacement_count}箇所を正規化しました。</p>
              {added.normalization_warning && <ErrorNotice>{added.normalization_warning}</ErrorNotice>}
            </div>
          )}
          {add.isError && !uploadOpen && <ErrorNotice>議事録を追加できませんでした</ErrorNotice>}
          {remove.isError && <ErrorNotice>議事録を削除できませんでした</ErrorNotice>}
          {!started && <p className="text-sm text-[var(--color-warm-gray-500)]">会議の開始後に抽出できます</p>}
          {knowledge.length > 0 && started && (
            <div className="space-y-2">
              <Button
                variant="secondary"
                isLoading={extract.isPending}
                disabled={add.isPending || remove.isPending}
                onClick={() => extract.mutate()}
              >
                {needsExtraction ? 'メモリ抽出を再実行' : 'メモリを再抽出'}
              </Button>
              <p className="text-xs text-[var(--color-warm-gray-500)]">
                決定事項・アクションアイテム・未解決の論点をチームメモリに反映します。
              </p>
            </div>
          )}
          {extract.isError && (
            <ErrorNotice>メモリの抽出に失敗しました。議事録は保存されています。抽出を再実行してください</ErrorNotice>
          )}
          {extract.data && !extract.isPending && (
            <output className="block text-sm">
              抽出完了: {extract.data.created}件追加、{extract.data.closed}件解決
            </output>
          )}
          {extract.data?.truncated && !extract.isPending && (
            <ErrorNotice>議事録が文字数の上限を超えたため、一部を切り詰めて抽出しました。</ErrorNotice>
          )}
          {uploadOpen && (
            <KnowledgeUpload
              pending={add.isPending}
              canExtract={started}
              failed={add.isError}
              onClose={() => setUploadOpen(false)}
              onUpload={(text) => add.mutate({ source: 'upload', text }, { onSuccess: afterAdded })}
            />
          )}
        </>
      )}
      {selected && <KnowledgeDetail seriesId={seriesId} knowledgeId={selected} onClose={() => setSelected(null)} />}
    </Card>
  )
}
