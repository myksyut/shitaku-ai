import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button, Card } from '../../components/ui'
import { ApiError } from '../../lib/api-client'
import { useGoogleIntegrations } from '../google/hooks'
import { hasCalendarReadScope } from '../google/scopes'
import { useCalendarEvents, useClaimSeries } from './hooks'
import { Badge, ErrorNotice } from './SeriesUi'
import type { CalendarEventChoice } from './types'

function claimErrorMessage(error: Error) {
  if (error instanceof ApiError) {
    switch (error.status) {
      case 403:
        return '作成者のカレンダーの参加者に含まれていません（招待直後なら数分後に再試行してください）'
      case 422:
        return 'この予定の参加者ではありません'
      case 404:
        return 'カレンダーに予定が見つかりません'
      case 409:
        return '作成者のカレンダーを読み取れません。作成者にGoogle連携の確認を依頼してください'
    }
  }
  return '定例を追加できませんでした。もう一度お試しください'
}

export function CalendarEventPicker() {
  const navigate = useNavigate()
  const integrations = useGoogleIntegrations()
  const [chosen, setChosen] = useState<string | null>(null)
  const available = integrations.data?.filter((integration) => hasCalendarReadScope(integration.granted_scopes)) ?? []
  const integrationId = available.find((integration) => integration.id === chosen)?.id ?? available[0]?.id ?? null
  const events = useCalendarEvents(integrationId)
  const claim = useClaimSeries()

  function open(event: CalendarEventChoice) {
    if (event.series_id) {
      navigate(`/series/${event.series_id}`)
    } else if (integrationId) {
      claim.mutate(
        { google_integration_id: integrationId, calendar_event_id: event.calendar_event_id },
        {
          onSuccess: ({ series }) => navigate(`/series/${series.id}`),
        },
      )
    }
  }

  return (
    <Card className="space-y-4">
      <h2 className="text-lg font-bold">カレンダーから追加</h2>
      <p className="text-sm text-[var(--color-warm-gray-500)]">
        繰り返し予定を選ぶと、カレンダーの参加者と準備を共有できます。
      </p>
      {integrations.isPending ? (
        <output>連携を読み込み中...</output>
      ) : integrations.isError ? (
        <ErrorNotice>Google連携を読み込めませんでした</ErrorNotice>
      ) : integrations.data.length === 0 ? (
        <p>
          カレンダーの読み取り権限があるGoogleアカウントを
          <Link to="/settings/google" className="underline">
            連携してください
          </Link>
          。
        </p>
      ) : (
        <>
          <label className="label" htmlFor="calendar-account">
            Googleアカウント
          </label>
          <select
            id="calendar-account"
            className="input"
            value={integrationId ?? ''}
            disabled={claim.isPending}
            onChange={(event) => {
              setChosen(event.target.value)
              claim.reset()
            }}
          >
            {!integrationId && <option value="">読み取り権限のあるアカウントがありません</option>}
            {integrations.data.map((integration) => (
              <option
                key={integration.id}
                value={integration.id}
                disabled={!hasCalendarReadScope(integration.granted_scopes)}
              >
                {integration.email}
                {!hasCalendarReadScope(integration.granted_scopes) && '（カレンダーの読み取り権限を追加してください）'}
              </option>
            ))}
          </select>
          {!integrationId ? (
            <p>
              カレンダーの読み取り権限を追加してください。
              <Link to="/settings/google" className="underline">
                Google連携設定
              </Link>
            </p>
          ) : events.isPending ? (
            <output>予定を読み込み中...</output>
          ) : events.isError ? (
            <ErrorNotice>カレンダーの予定を読み込めませんでした</ErrorNotice>
          ) : events.data?.length === 0 ? (
            <p>繰り返し予定がありません</p>
          ) : (
            <ul className="divide-y divide-[var(--color-cream-300)]">
              {events.data?.map((event) => (
                <li key={event.calendar_event_id} className="flex flex-wrap items-center justify-between gap-3 py-4">
                  <div className="space-y-1">
                    <p className="font-bold">{event.title}</p>
                    <Badge>参加者{event.attendee_count}人</Badge>
                  </div>
                  <Button
                    variant={event.series_id ? 'secondary' : 'primary'}
                    disabled={claim.isPending}
                    onClick={() => open(event)}
                  >
                    {event.series_id ? '開く' : 'Shitakuで準備する'}
                  </Button>
                </li>
              ))}
            </ul>
          )}
          {claim.isPending && <output>定例を追加中...</output>}
          {claim.error && <ErrorNotice>{claimErrorMessage(claim.error)}</ErrorNotice>}
        </>
      )}
    </Card>
  )
}
