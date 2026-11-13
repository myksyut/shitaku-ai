import { Modal } from '../../components/ui'
import { useKnowledge } from './hooks'
import { ErrorNotice, formatStart } from './SeriesUi'

export function KnowledgeDetail({
  seriesId,
  knowledgeId,
  onClose,
}: {
  seriesId: string
  knowledgeId: string
  onClose: () => void
}) {
  const knowledge = useKnowledge(seriesId, knowledgeId)
  return (
    <Modal isOpen onClose={onClose} title={knowledge.data?.title ?? 'ナレッジ詳細'} size="lg">
      {knowledge.isPending ? (
        <output>議事録を読み込み中...</output>
      ) : knowledge.isError ? (
        <ErrorNotice>議事録を読み込めませんでした</ErrorNotice>
      ) : (
        <div className="space-y-4">
          <p className="text-sm text-[var(--color-warm-gray-500)]">
            {knowledge.data.source === 'meet_transcript' ? 'Meetトランスクリプト' : 'アップロード'} /{' '}
            {formatStart(knowledge.data.created_at)}
          </p>
          <div className="max-h-[60vh] overflow-auto whitespace-pre-wrap break-words rounded-xl bg-[var(--color-cream-100)] p-4 text-sm">
            {knowledge.data.text}
          </div>
        </div>
      )}
    </Modal>
  )
}
