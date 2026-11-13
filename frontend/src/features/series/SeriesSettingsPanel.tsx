import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button, Card, Input, Textarea } from '../../components/ui'
import { useSlackChannels, useSlackIntegrations } from '../slack/hooks'
import { useDeleteSeries, useSaveSeriesSettings, useSyncSeriesCalendar } from './hooks'
import { ErrorNotice, formatStart } from './SeriesUi'
import type { SeriesDetail } from './types'

export function SeriesSettingsPanel({ series }: { series: SeriesDetail }) {
  const navigate = useNavigate()
  const save = useSaveSeriesSettings(series.id)
  const sync = useSyncSeriesCalendar(series.id)
  const remove = useDeleteSeries()
  const integrations = useSlackIntegrations()
  const [description, setDescription] = useState(series.settings.description ?? '')
  const [minutesCount, setMinutesCount] = useState(String(series.settings.minutes_count))
  const [messageDays, setMessageDays] = useState(String(series.settings.slack_message_days))
  const [integrationId, setIntegrationId] = useState(series.slack?.integration_id ?? '')
  const [channelIds, setChannelIds] = useState(series.slack?.channels.map((channel) => channel.id) ?? [])
  const channels = useSlackChannels(integrationId)

  function submit(event: React.FormEvent) {
    event.preventDefault()
    save.mutate({
      description: description.trim() || null,
      minutes_count: Number(minutesCount),
      slack_message_days: Number(messageDays),
      slack: integrationId ? { integration_id: integrationId, channel_ids: channelIds } : null,
    })
  }

  return (
    <div className="space-y-5">
      <Card>
        <form onSubmit={submit} className="space-y-4">
          <h2 className="text-lg font-bold">定例の設定</h2>
          <Textarea
            id="series-description"
            label="説明"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            rows={3}
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              id="minutes-count"
              label="参照する議事録の件数"
              type="number"
              min={0}
              required
              value={minutesCount}
              onChange={(event) => setMinutesCount(event.target.value)}
            />
            <Input
              id="slack-days"
              label="Slackの参照日数"
              type="number"
              min={0}
              required
              value={messageDays}
              onChange={(event) => setMessageDays(event.target.value)}
            />
          </div>
          <div className="space-y-2">
            <label htmlFor="series-slack" className="label">
              Slack連携
            </label>
            <select
              id="series-slack"
              className="input"
              value={integrationId}
              onChange={(event) => {
                setIntegrationId(event.target.value)
                setChannelIds([])
              }}
              disabled={integrations.isPending}
            >
              <option value="">連携しない</option>
              {integrationId && !integrations.data?.some((integration) => integration.id === integrationId) && (
                <option value={integrationId}>保存済みの連携（接続を確認してください）</option>
              )}
              {integrations.data?.map((integration) => (
                <option key={integration.id} value={integration.id}>
                  {integration.workspace_name}
                </option>
              ))}
            </select>
            <Link to="/settings/slack" className="text-sm underline">
              Slack連携を管理
            </Link>
            {integrations.isError && <ErrorNotice>Slack連携を読み込めませんでした</ErrorNotice>}
          </div>
          {integrationId && (
            <fieldset className="space-y-2">
              <legend className="label">参照するチャンネル</legend>
              {channels.isPending ? (
                <output>チャンネルを読み込み中...</output>
              ) : channels.isError ? (
                <ErrorNotice>チャンネルを読み込めませんでした</ErrorNotice>
              ) : channels.data.length === 0 ? (
                <p>選択できるチャンネルがありません</p>
              ) : (
                channels.data.map((channel) => (
                  <label key={channel.id} className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={channelIds.includes(channel.id)}
                      onChange={(event) =>
                        setChannelIds(
                          event.target.checked
                            ? [...channelIds, channel.id]
                            : channelIds.filter((id) => id !== channel.id),
                        )
                      }
                    />
                    #{channel.name}
                  </label>
                ))
              )}
            </fieldset>
          )}
          {save.isError && <ErrorNotice>設定を保存できませんでした。入力内容を確認してください</ErrorNotice>}
          {save.isSuccess && <output>設定を保存しました</output>}
          <Button type="submit" isLoading={save.isPending}>
            設定を保存
          </Button>
        </form>
      </Card>
      <Card className="space-y-3">
        <h2 className="text-lg font-bold">カレンダー同期</h2>
        <p className="text-sm">最終同期: {formatStart(series.calendar.synced_at)}</p>
        {series.calendar.error && <ErrorNotice>{series.calendar.error}</ErrorNotice>}
        {!series.calendar.google_connected && (
          <p>
            Google連携が解除されているため同期は停止しています。
            <Link className="underline" to="/settings/google">
              Google連携を確認
            </Link>
          </p>
        )}
        <Button
          variant="secondary"
          disabled={!series.calendar.google_connected}
          isLoading={sync.isPending}
          onClick={() => sync.mutate()}
        >
          カレンダーを同期
        </Button>
        {sync.isError && <ErrorNotice>カレンダーを同期できませんでした</ErrorNotice>}
        {sync.isSuccess && <output>カレンダーを同期しました</output>}
      </Card>
      <Card className="space-y-3">
        <h2 className="text-lg font-bold">定例の削除</h2>
        <p className="text-sm">議事録やチームメモリを含め、この定例を全参加者から削除します。</p>
        <Button
          variant="danger"
          isLoading={remove.isPending}
          onClick={() => {
            if (window.confirm('この定例とすべての議事録・メモリを削除しますか？この操作は取り消せません。'))
              remove.mutate(series.id, { onSuccess: () => navigate('/') })
          }}
        >
          定例を削除
        </Button>
        {remove.isError && <ErrorNotice>定例を削除できませんでした</ErrorNotice>}
      </Card>
    </div>
  )
}
