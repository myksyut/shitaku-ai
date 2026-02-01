/**
 * DictionarySection component for displaying and managing dictionary entries
 * within an agent's detail page
 */
import { useState } from 'react'
import { Button, Card } from '../../components/ui'
import { AgentDictionaryForm } from './AgentDictionaryForm'
import { useAgentDictionaryEntries, useDeleteAgentDictionaryEntry } from './hooks'
import { CATEGORY_LABELS, type DictionaryEntry } from './types'

interface DictionarySectionProps {
  agentId: string
}

export function DictionarySection({ agentId }: DictionarySectionProps) {
  const { data: entries, isLoading, error } = useAgentDictionaryEntries(agentId)
  const deleteEntry = useDeleteAgentDictionaryEntry(agentId)
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [editingEntry, setEditingEntry] = useState<DictionaryEntry | null>(null)

  const handleAdd = () => {
    setEditingEntry(null)
    setIsFormOpen(true)
  }

  const handleEdit = (entry: DictionaryEntry) => {
    setEditingEntry(entry)
    setIsFormOpen(true)
  }

  const handleDelete = async (entryId: string) => {
    if (window.confirm('この辞書エントリを削除しますか？')) {
      await deleteEntry.mutateAsync(entryId)
    }
  }

  const handleFormClose = () => {
    setIsFormOpen(false)
    setEditingEntry(null)
  }

  if (isLoading) {
    return (
      <div
        style={{
          textAlign: 'center',
          padding: 'var(--space-6)',
          color: 'var(--color-warm-gray-500)',
        }}
      >
        読み込み中...
      </div>
    )
  }

  if (error) {
    return (
      <div className="alert alert-error" style={{ color: 'var(--color-error)' }}>
        辞書の読み込みに失敗しました
      </div>
    )
  }

  return (
    <section>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 'var(--space-4)',
        }}
      >
        <h2
          style={{
            fontSize: 'var(--font-size-lg)',
            fontWeight: 700,
            color: 'var(--color-warm-gray-800)',
            margin: 0,
          }}
        >
          辞書
        </h2>
        <Button variant="secondary" onClick={handleAdd}>
          辞書を追加
        </Button>
      </div>

      {entries?.length === 0 ? (
        <div
          style={{
            textAlign: 'center',
            padding: 'var(--space-8)',
            color: 'var(--color-warm-gray-500)',
            background: 'var(--color-cream-200)',
            borderRadius: 'var(--radius-md)',
          }}
        >
          辞書エントリがありません
        </div>
      ) : (
        <div
          style={{
            display: 'grid',
            gap: 'var(--space-4)',
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
          }}
        >
          {entries?.map((entry) => (
            <Card key={entry.id}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  justifyContent: 'space-between',
                }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <h3
                    style={{
                      fontSize: 'var(--font-size-base)',
                      fontWeight: 600,
                      color: 'var(--color-warm-gray-800)',
                      margin: 0,
                    }}
                  >
                    {entry.canonical_name}
                  </h3>
                  {entry.category && (
                    <span
                      style={{
                        display: 'inline-block',
                        marginTop: 'var(--space-1)',
                        padding: '2px 8px',
                        fontSize: 'var(--font-size-xs)',
                        background: 'var(--color-cream-300)',
                        borderRadius: 'var(--radius-full)',
                        color: 'var(--color-warm-gray-600)',
                      }}
                    >
                      {CATEGORY_LABELS[entry.category]}
                    </span>
                  )}
                </div>
                <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                  <Button
                    variant="ghost"
                    onClick={() => handleEdit(entry)}
                    aria-label="編集"
                    style={{ padding: 'var(--space-1) var(--space-2)' }}
                  >
                    編集
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() => handleDelete(entry.id)}
                    disabled={deleteEntry.isPending}
                    aria-label="削除"
                    style={{
                      padding: 'var(--space-1) var(--space-2)',
                      color: 'var(--color-error)',
                    }}
                  >
                    削除
                  </Button>
                </div>
              </div>
              {entry.aliases.length > 0 && (
                <p
                  style={{
                    marginTop: 'var(--space-2)',
                    fontSize: 'var(--font-size-sm)',
                    color: 'var(--color-warm-gray-600)',
                  }}
                >
                  表記揺れ: {entry.aliases.length}件
                </p>
              )}
              {entry.description && (
                <p
                  style={{
                    marginTop: 'var(--space-2)',
                    fontSize: 'var(--font-size-sm)',
                    color: 'var(--color-warm-gray-600)',
                    lineHeight: 1.5,
                  }}
                >
                  {entry.description}
                </p>
              )}
            </Card>
          ))}
        </div>
      )}

      {isFormOpen && <AgentDictionaryForm agentId={agentId} entry={editingEntry} onClose={handleFormClose} />}
    </section>
  )
}
