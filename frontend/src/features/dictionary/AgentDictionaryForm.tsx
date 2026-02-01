/**
 * AgentDictionaryForm component for creating/editing dictionary entries
 * Modal form with canonical_name, category, aliases, and description fields
 */
import type { KeyboardEvent } from 'react'
import { useState } from 'react'
import { Button, Modal } from '../../components/ui'
import { useCreateAgentDictionaryEntry, useUpdateAgentDictionaryEntry } from './hooks'
import { CATEGORY_LABELS, DICTIONARY_CATEGORIES, type DictionaryCategory, type DictionaryEntry } from './types'

interface AgentDictionaryFormProps {
  agentId: string
  entry: DictionaryEntry | null
  onClose: () => void
}

export function AgentDictionaryForm({ agentId, entry, onClose }: AgentDictionaryFormProps) {
  const isEditing = entry !== null
  const createEntry = useCreateAgentDictionaryEntry(agentId)
  const updateEntry = useUpdateAgentDictionaryEntry(agentId)

  const [canonicalName, setCanonicalName] = useState(entry?.canonical_name ?? '')
  const [category, setCategory] = useState<DictionaryCategory>(entry?.category ?? 'term')
  const [aliases, setAliases] = useState<string[]>(entry?.aliases ?? [])
  const [aliasInput, setAliasInput] = useState('')
  const [description, setDescription] = useState(entry?.description ?? '')
  const [error, setError] = useState<string | null>(null)

  const handleAliasKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      const value = aliasInput.trim().replace(',', '')
      if (value && !aliases.includes(value)) {
        setAliases([...aliases, value])
      }
      setAliasInput('')
    }
  }

  const removeAlias = (aliasToRemove: string) => {
    setAliases(aliases.filter((a) => a !== aliasToRemove))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!canonicalName.trim()) {
      setError('正式名称は必須です')
      return
    }

    try {
      if (isEditing && entry) {
        await updateEntry.mutateAsync({
          entryId: entry.id,
          data: {
            canonical_name: canonicalName,
            category,
            aliases,
            description: description || null,
          },
        })
      } else {
        await createEntry.mutateAsync({
          canonical_name: canonicalName,
          category,
          aliases,
          description: description || null,
        })
      }
      onClose()
    } catch {
      setError('保存に失敗しました')
    }
  }

  const isPending = createEntry.isPending || updateEntry.isPending

  return (
    <Modal isOpen={true} onClose={onClose} title={isEditing ? '辞書エントリを編集' : '辞書エントリを追加'}>
      <form onSubmit={handleSubmit}>
        {error && (
          <div className="alert alert-error" style={{ marginBottom: 'var(--space-4)' }}>
            {error}
          </div>
        )}

        <div style={{ marginBottom: 'var(--space-4)' }}>
          <label
            htmlFor="canonicalName"
            style={{
              display: 'block',
              fontSize: 'var(--font-size-sm)',
              fontWeight: 600,
              color: 'var(--color-warm-gray-700)',
              marginBottom: 'var(--space-2)',
            }}
          >
            正式名称 <span style={{ color: 'var(--color-error)' }}>*</span>
          </label>
          <input
            id="canonicalName"
            type="text"
            value={canonicalName}
            onChange={(e) => setCanonicalName(e.target.value)}
            className="input"
            aria-required="true"
          />
        </div>

        <div style={{ marginBottom: 'var(--space-4)' }}>
          <label
            htmlFor="category"
            style={{
              display: 'block',
              fontSize: 'var(--font-size-sm)',
              fontWeight: 600,
              color: 'var(--color-warm-gray-700)',
              marginBottom: 'var(--space-2)',
            }}
          >
            カテゴリ <span style={{ color: 'var(--color-error)' }}>*</span>
          </label>
          <select
            id="category"
            value={category}
            onChange={(e) => setCategory(e.target.value as DictionaryCategory)}
            className="input"
            aria-required="true"
          >
            {DICTIONARY_CATEGORIES.map((cat) => (
              <option key={cat} value={cat}>
                {CATEGORY_LABELS[cat]}
              </option>
            ))}
          </select>
        </div>

        <div style={{ marginBottom: 'var(--space-4)' }}>
          <label
            htmlFor="aliases"
            style={{
              display: 'block',
              fontSize: 'var(--font-size-sm)',
              fontWeight: 600,
              color: 'var(--color-warm-gray-700)',
              marginBottom: 'var(--space-2)',
            }}
          >
            表記揺れ
          </label>
          {aliases.length > 0 && (
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: 'var(--space-2)',
                marginBottom: 'var(--space-2)',
              }}
            >
              {aliases.map((alias) => (
                <span
                  key={alias}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    padding: '4px 8px',
                    background: 'var(--color-cream-300)',
                    borderRadius: 'var(--radius-full)',
                    fontSize: 'var(--font-size-sm)',
                  }}
                >
                  {alias}
                  <button
                    type="button"
                    onClick={() => removeAlias(alias)}
                    style={{
                      marginLeft: 'var(--space-1)',
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      color: 'var(--color-warm-gray-500)',
                      padding: 0,
                      lineHeight: 1,
                    }}
                    aria-label={`${alias}を削除`}
                  >
                    x
                  </button>
                </span>
              ))}
            </div>
          )}
          <input
            id="aliases"
            type="text"
            value={aliasInput}
            onChange={(e) => setAliasInput(e.target.value)}
            onKeyDown={handleAliasKeyDown}
            placeholder="Enter または カンマ で追加"
            className="input"
          />
        </div>

        <div style={{ marginBottom: 'var(--space-6)' }}>
          <label
            htmlFor="description"
            style={{
              display: 'block',
              fontSize: 'var(--font-size-sm)',
              fontWeight: 600,
              color: 'var(--color-warm-gray-700)',
              marginBottom: 'var(--space-2)',
            }}
          >
            説明
          </label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="input"
            rows={3}
          />
        </div>

        <div
          style={{
            display: 'flex',
            justifyContent: 'flex-end',
            gap: 'var(--space-3)',
          }}
        >
          <Button variant="ghost" onClick={onClose} disabled={isPending}>
            キャンセル
          </Button>
          <Button variant="primary" type="submit" isLoading={isPending}>
            {isEditing ? '更新' : '作成'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
