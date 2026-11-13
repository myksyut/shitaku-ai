import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Button, Textarea } from '../../components/ui'
import { useSaveAgenda } from './hooks'
import { ErrorNotice } from './SeriesUi'
import type { Agenda } from './types'

export function AgendaEditor({ seriesId, agenda, canEdit }: { seriesId: string; agenda: Agenda; canEdit: boolean }) {
  const [isEditing, setIsEditing] = useState(false)
  const [content, setContent] = useState(agenda.content)
  const [copied, setCopied] = useState(false)
  const [copyError, setCopyError] = useState(false)
  const save = useSaveAgenda(seriesId, agenda.occurrence_id)

  async function copy() {
    setCopyError(false)
    try {
      await navigator.clipboard.writeText(content)
      setCopied(true)
    } catch {
      setCopyError(true)
    }
  }

  async function submit() {
    try {
      await save.mutateAsync(content.trim())
      setIsEditing(false)
    } catch {
      return
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap justify-between gap-3">
        <div className="flex gap-2">
          <Button variant={!isEditing ? 'secondary' : 'ghost'} onClick={() => setIsEditing(false)}>
            プレビュー
          </Button>
          {canEdit && (
            <Button variant={isEditing ? 'secondary' : 'ghost'} onClick={() => setIsEditing(true)}>
              編集
            </Button>
          )}
        </div>
        <Button variant="ghost" onClick={copy}>
          {copied ? 'コピー済み' : 'コピー'}
        </Button>
      </div>
      {isEditing && canEdit ? (
        <Textarea
          id="agenda-content"
          label="アジェンダの内容"
          rows={16}
          value={content}
          disabled={save.isPending}
          onChange={(event) => {
            setContent(event.target.value)
            setCopied(false)
          }}
          className="font-mono text-sm"
        />
      ) : (
        <div className="markdown-preview max-h-[70vh] overflow-auto rounded-2xl border border-[var(--color-cream-300)] bg-[var(--color-cream-50)] p-5 text-sm leading-relaxed text-[var(--color-warm-gray-700)]">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              h1: ({ children }) => <h1 className="mb-2 mt-4 text-2xl font-bold">{children}</h1>,
              h2: ({ children }) => <h2 className="mb-2 mt-4 text-xl font-bold">{children}</h2>,
              h3: ({ children }) => <h3 className="mb-2 mt-3 text-lg font-semibold">{children}</h3>,
              ul: ({ children }) => <ul className="mb-3 ml-6 list-disc">{children}</ul>,
              ol: ({ children }) => <ol className="mb-3 ml-6 list-decimal">{children}</ol>,
              li: ({ children }) => <li className="mb-1">{children}</li>,
              p: ({ children }) => <p className="mb-3">{children}</p>,
              code: ({ children }) => (
                <code className="rounded bg-[var(--color-cream-200)] px-1 font-mono">{children}</code>
              ),
              pre: ({ children }) => (
                <pre className="mb-3 overflow-auto rounded-lg bg-[var(--color-cream-200)] p-4">{children}</pre>
              ),
              table: ({ children }) => <table className="mb-3 w-full border-collapse">{children}</table>,
              th: ({ children }) => (
                <th className="border border-[var(--color-cream-300)] bg-[var(--color-cream-200)] p-2 text-left">
                  {children}
                </th>
              ),
              td: ({ children }) => <td className="border border-[var(--color-cream-300)] p-2">{children}</td>,
              blockquote: ({ children }) => (
                <blockquote className="mb-3 border-l-4 border-[var(--color-primary-300)] pl-4 italic">
                  {children}
                </blockquote>
              ),
            }}
          >
            {content}
          </ReactMarkdown>
        </div>
      )}
      {copyError && <ErrorNotice>コピーに失敗しました</ErrorNotice>}
      {save.isError && <ErrorNotice>アジェンダを保存できませんでした</ErrorNotice>}
      {isEditing && canEdit && (
        <div className="flex justify-end gap-3">
          <Button
            variant="ghost"
            disabled={save.isPending}
            onClick={() => {
              setContent(agenda.content)
              setCopied(false)
              setIsEditing(false)
            }}
          >
            キャンセル
          </Button>
          <Button isLoading={save.isPending} disabled={!content.trim()} onClick={submit}>
            保存する
          </Button>
        </div>
      )}
    </div>
  )
}
