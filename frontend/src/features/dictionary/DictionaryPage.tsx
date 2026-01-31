import { useState } from 'react'
import { DictionaryForm } from './DictionaryForm'
import { useDeleteDictionaryEntry, useDictionaryEntries } from './hooks'
import type { DictionaryEntry } from './types'

export function DictionaryPage() {
  const [editingEntry, setEditingEntry] = useState<DictionaryEntry | null>(null)
  const [isFormOpen, setIsFormOpen] = useState(false)

  const { data: entries, isLoading, error } = useDictionaryEntries()
  const deleteMutation = useDeleteDictionaryEntry()

  const handleDelete = async (id: string) => {
    if (window.confirm('削除してもよろしいですか？')) {
      await deleteMutation.mutateAsync(id)
    }
  }

  const handleEdit = (entry: DictionaryEntry) => {
    setEditingEntry(entry)
    setIsFormOpen(true)
  }

  const handleCreate = () => {
    setEditingEntry(null)
    setIsFormOpen(true)
  }

  const handleFormClose = () => {
    setEditingEntry(null)
    setIsFormOpen(false)
  }

  if (isLoading) return <div className="p-4">読み込み中...</div>
  if (error) return <div className="p-4 text-red-500">エラーが発生しました</div>

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">ユビキタス言語辞書</h1>
        <button type="button" onClick={handleCreate} className="bg-blue-500 text-white px-4 py-2 rounded">
          新規作成
        </button>
      </div>

      <div className="space-y-2">
        {entries?.map((entry) => (
          <div key={entry.id} className="border rounded p-4 flex justify-between items-start">
            <div>
              <div className="font-bold">{entry.canonical_name}</div>
              {entry.description && <div className="text-sm mt-1 text-gray-600">{entry.description}</div>}
            </div>
            <div className="flex gap-2">
              <button type="button" onClick={() => handleEdit(entry)} className="text-blue-500 hover:underline">
                編集
              </button>
              <button type="button" onClick={() => handleDelete(entry.id)} className="text-red-500 hover:underline">
                削除
              </button>
            </div>
          </div>
        ))}
        {entries?.length === 0 && (
          <div className="text-gray-500 text-center py-8">辞書エントリがありません。新規作成してください。</div>
        )}
      </div>

      {isFormOpen && <DictionaryForm entry={editingEntry} onClose={handleFormClose} />}
    </div>
  )
}
