import { describe, expect, it } from 'vitest'
import { calendarSyncErrorMessage, syncErrorMessage } from './sync-errors'

describe('integration error messages', () => {
  it.each([
    ['calendar', 'not_connected', '作成者のGoogle連携が切れています'],
    ['calendar', 'scope_missing', 'Googleカレンダーの権限が不足しています'],
    ['calendar', 'revoked', 'Google連携の許可が取り消されています'],
    ['calendar', 'attendees_omitted', '招待客一覧を取得できませんでした（ゲストリスト非公開）'],
    ['calendar', 'event_not_found', 'カレンダーに予定が見つかりません'],
    ['calendar', 'calendar_unavailable', 'カレンダーを読み込めませんでした'],
    ['slack', 'not_connected', 'Slack連携がありません'],
    ['slack', 'not_in_channel', 'Slackボットがチャンネルに参加していません'],
    ['slack', 'rate_limited', 'Slackの利用制限に達しました'],
    ['slack', 'slack_unavailable', 'Slackを読み込めませんでした'],
  ] as const)('translates %s code %s', (service, code, expected) => {
    expect(syncErrorMessage(service, code)).toBe(expected)
  })

  it.each(['calendar', 'slack'] as const)('uses a safe fallback for unknown %s codes', (service) => {
    expect(syncErrorMessage(service, 'new_backend_code')).toBe('同期でエラーが発生しました')
    expect(syncErrorMessage(service, 'toString')).toBe('同期でエラーが発生しました')
  })

  it.each(['not_connected', 'scope_missing', 'new_backend_code'])('directs members to the creator for %s', (code) => {
    expect(calendarSyncErrorMessage(code, 'member')).toBe(
      'カレンダー同期でエラーが発生しています（作成者に確認してください）',
    )
  })

  it('shows the specific calendar message to the creator', () => {
    expect(calendarSyncErrorMessage('not_connected', 'creator')).toBe('作成者のGoogle連携が切れています')
  })
})
