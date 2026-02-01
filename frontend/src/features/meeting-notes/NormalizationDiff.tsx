/**
 * Normalization diff view component
 * Shows before/after comparison of normalized text
 */

import type { MeetingNote } from './types'

interface Props {
  note: MeetingNote
  onClose: () => void
}

export function NormalizationDiff({ note, onClose }: Props) {
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('ja-JP', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h2 className="text-xl font-bold">議事録詳細</h2>
            <p className="text-sm text-gray-500 mt-1">MTG日: {formatDate(note.meeting_date)}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl leading-none"
            aria-label="閉じる"
          >
            &times;
          </button>
        </div>

        {note.is_normalized ? (
          <div className="grid md:grid-cols-2 gap-4">
            {/* 元テキスト */}
            <div>
              <h3 className="font-medium mb-2 text-gray-600">元のテキスト</h3>
              <div className="border rounded p-3 bg-gray-50 text-sm font-mono whitespace-pre-wrap max-h-96 overflow-y-auto">
                {note.original_text}
              </div>
            </div>

            {/* 正規化後テキスト */}
            <div>
              <h3 className="font-medium mb-2 text-green-600">正規化後</h3>
              <div className="border rounded p-3 bg-green-50 text-sm font-mono whitespace-pre-wrap max-h-96 overflow-y-auto">
                {note.normalized_text}
              </div>
            </div>
          </div>
        ) : (
          <div>
            <h3 className="font-medium mb-2 text-gray-600">テキスト（変更なし）</h3>
            <div className="border rounded p-3 bg-gray-50 text-sm font-mono whitespace-pre-wrap max-h-96 overflow-y-auto">
              {note.original_text}
            </div>
            <p className="text-sm text-gray-500 mt-2">このテキストは正規化による変更がありませんでした。</p>
          </div>
        )}

        <div className="flex justify-end mt-4">
          <button type="button" onClick={onClose} className="px-4 py-2 border rounded hover:bg-gray-50">
            閉じる
          </button>
        </div>
      </div>
    </div>
  )
}
