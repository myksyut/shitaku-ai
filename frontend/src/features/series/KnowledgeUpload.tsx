import { useState } from 'react'
import { Button, Modal, Textarea } from '../../components/ui'
import { ErrorNotice } from './SeriesUi'

export function KnowledgeUpload({
  onUpload,
  onClose,
  pending,
  failed,
}: {
  onUpload: (text: string) => void
  onClose: () => void
  pending: boolean
  failed: boolean
}) {
  const [text, setText] = useState('')
  return (
    <Modal isOpen onClose={onClose} title="議事録・ナレッジを追加">
      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault()
          if (text.trim()) onUpload(text.trim())
        }}
      >
        <Textarea
          id="knowledge-text"
          label="議事録・ナレッジのテキスト"
          value={text}
          onChange={(event) => setText(event.target.value)}
          rows={15}
          required
          disabled={pending}
          hint="辞書に登録された表記揺れは自動的に正規化されます"
        />
        {failed && <ErrorNotice>議事録を追加できませんでした。内容を確認して再度お試しください</ErrorNotice>}
        <div className="flex justify-end gap-3">
          <Button type="button" variant="ghost" onClick={onClose} disabled={pending}>
            キャンセル
          </Button>
          <Button type="submit" isLoading={pending} disabled={!text.trim()}>
            追加して抽出
          </Button>
        </div>
      </form>
    </Modal>
  )
}
