import { useState } from 'react'
import { useCreateDictionaryEntry, useUpdateDictionaryEntry } from './hooks'
import type { DictionaryCategory, DictionaryEntry } from './types'
import { CATEGORY_LABELS, DICTIONARY_CATEGORIES } from './types'

interface Props {
  entry: DictionaryEntry | null
  onClose: () => void
}

export function DictionaryForm({ entry, onClose }: Props) {
  const [canonicalName, setCanonicalName] = useState(entry?.canonical_name ?? '')
  const [category, setCategory] = useState<DictionaryCategory>(entry?.category ?? 'person')
  const [description, setDescription] = useState(entry?.description ?? '')
  const [error, setError] = useState<string | null>(null)

  const createMutation = useCreateDictionaryEntry()
  const updateMutation = useUpdateDictionaryEntry()

  const isEditing = !!entry

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    try {
      if (isEditing) {
        await updateMutation.mutateAsync({
          id: entry.id,
          data: {
            canonical_name: canonicalName,
            description: description || null,
          },
        })
      } else {
        await createMutation.mutateAsync({
          canonical_name: canonicalName,
          category,
          description: description || null,
        })
      }
      onClose()
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message)
      }
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <h2 className="text-xl font-bold mb-4">{isEditing ? '辞書エントリ編集' : '辞書エントリ作成'}</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="canonical-name" className="block text-sm font-medium mb-1">
              正式名称
            </label>
            <input
              id="canonical-name"
              type="text"
              value={canonicalName}
              onChange={(e) => setCanonicalName(e.target.value)}
              className="w-full border rounded px-3 py-2"
              required
              maxLength={100}
            />
          </div>

          <div>
            <label htmlFor="category" className="block text-sm font-medium mb-1">
              カテゴリ
            </label>
            <select
              id="category"
              value={category}
              onChange={(e) => setCategory(e.target.value as DictionaryCategory)}
              className="w-full border rounded px-3 py-2"
              required
            >
              {DICTIONARY_CATEGORIES.map((cat) => (
                <option key={cat} value={cat}>
                  {CATEGORY_LABELS[cat]}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="description" className="block text-sm font-medium mb-1">
              説明（LLMへのヒント）
            </label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full border rounded px-3 py-2"
              rows={3}
              maxLength={500}
              placeholder="例: フロントエンド担当、チームA所属"
            />
          </div>

          {error && <div className="text-red-500 text-sm">{error}</div>}

          <div className="flex justify-end gap-2">
            <button type="button" onClick={onClose} className="px-4 py-2 border rounded">
              キャンセル
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-500 text-white rounded"
              disabled={createMutation.isPending || updateMutation.isPending}
            >
              {isEditing ? '更新' : '作成'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
