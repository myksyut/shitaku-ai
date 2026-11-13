import { describe, expect, it } from 'vitest'
import { calendarSyncErrorMessage, syncErrorMessage } from './sync-errors'

describe('integration error messages', () => {
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
