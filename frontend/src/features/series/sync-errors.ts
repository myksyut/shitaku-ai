import type { SeriesRole } from './types'

const SYNC_ERROR_MESSAGES: Record<'calendar' | 'slack' | 'proposal', Readonly<Record<string, string>>> = {
  calendar: {
    not_connected: '作成者のGoogle連携が切れています',
    scope_missing: 'Googleカレンダーの権限が不足しています',
    revoked: 'Google連携の許可が取り消されています',
    attendees_omitted: '招待客一覧を取得できませんでした（ゲストリスト非公開）',
    event_not_found: 'カレンダーに予定が見つかりません',
    calendar_unavailable: 'カレンダーを読み込めませんでした',
  },
  slack: {
    not_connected: 'Slack連携がありません',
    not_in_channel: 'Slackボットがチャンネルに参加していません',
    rate_limited: 'Slackの利用制限に達しました',
    slack_unavailable: 'Slackを読み込めませんでした',
  },
  proposal: {
    llm_unavailable: 'AIの提案を生成できませんでした（必須セクションは作成済み）',
  },
}

export function syncErrorMessage(service: keyof typeof SYNC_ERROR_MESSAGES, code: string) {
  const messages = SYNC_ERROR_MESSAGES[service]
  return Object.hasOwn(messages, code) ? messages[code] : '同期でエラーが発生しました'
}

export function calendarSyncErrorMessage(code: string, role: SeriesRole) {
  return role === 'member'
    ? 'カレンダー同期でエラーが発生しています（作成者に確認してください）'
    : syncErrorMessage('calendar', code)
}
