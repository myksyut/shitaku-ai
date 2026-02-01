/**
 * Agenda generation page component
 */

import { useState } from 'react'
import { AgendaEditor } from './AgendaEditor'
import { useGenerateAgenda } from './hooks'
import type { Agenda, DataSourcesInfo } from './types'

interface Props {
  agentId: string
  onClose: () => void
}

export function AgendaGeneratePage({ agentId, onClose }: Props) {
  const [generatedAgenda, setGeneratedAgenda] = useState<Agenda | null>(null)
  const [dataSources, setDataSources] = useState<DataSourcesInfo | null>(null)
  const [error, setError] = useState<string | null>(null)

  const generateMutation = useGenerateAgenda()

  const handleGenerate = async () => {
    setError(null)
    setGeneratedAgenda(null)
    setDataSources(null)

    try {
      const result = await generateMutation.mutateAsync({ agent_id: agentId })
      setGeneratedAgenda(result.agenda)
      setDataSources(result.data_sources)
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message)
      }
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold">アジェンダ生成</h2>
          <button type="button" onClick={onClose} className="text-gray-500 hover:text-gray-700" aria-label="閉じる">
            &times;
          </button>
        </div>

        {!generatedAgenda ? (
          <div className="text-center py-8">
            <p className="text-gray-600 mb-6">前回の議事録とSlack履歴を元に、次回MTGのアジェンダを自動生成します。</p>

            {error && <div className="text-red-500 text-sm bg-red-50 p-3 rounded mb-4">{error}</div>}

            <button
              type="button"
              onClick={handleGenerate}
              disabled={generateMutation.isPending}
              className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {generateMutation.isPending ? (
                <span className="flex items-center gap-2">
                  <span className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                  生成中...（最大30秒）
                </span>
              ) : (
                'アジェンダを生成'
              )}
            </button>

            {generateMutation.isPending && (
              <p className="text-sm text-gray-500 mt-4">
                前回議事録・Slack履歴・辞書を収集してアジェンダを生成しています...
              </p>
            )}
          </div>
        ) : (
          <div>
            {dataSources && (
              <div className="bg-gray-50 p-3 rounded mb-4 text-sm">
                <p className="font-medium mb-1">使用したデータソース:</p>
                <ul className="list-disc list-inside text-gray-600">
                  <li>前回議事録: {dataSources.has_meeting_note ? '参照しました' : 'なし'}</li>
                  <li>
                    Slackメッセージ: {dataSources.has_slack_messages ? `${dataSources.slack_message_count}件` : 'なし'}
                  </li>
                  <li>辞書エントリ: {dataSources.dictionary_entry_count}件</li>
                </ul>
              </div>
            )}

            <AgendaEditor agenda={generatedAgenda} onSaved={onClose} onCancel={onClose} />
          </div>
        )}
      </div>
    </div>
  )
}
