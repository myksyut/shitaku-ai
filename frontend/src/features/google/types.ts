export interface GoogleIntegration {
  id: string
  email: string
  granted_scopes: string[]
  created_at: string
  updated_at: string | null
}

export interface GoogleOAuthStartResponse {
  authorize_url: string
}

/** 定例MTGの頻度 */
export type MeetingFrequency = 'weekly' | 'biweekly' | 'monthly'

/** 定例MTG */
export interface RecurringMeeting {
  id: string
  google_event_id: string
  title: string
  frequency: MeetingFrequency
  attendees: string[]
  next_occurrence: string
  agent_id: string | null
}

/** 定例MTG一覧レスポンス */
export interface RecurringMeetingsResponse {
  meetings: RecurringMeeting[]
}

/** 同期結果レスポンス */
export interface SyncResultResponse {
  created: number
  updated: number
}
