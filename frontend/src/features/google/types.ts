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

/** トランスクリプトエントリ */
export interface TranscriptEntry {
  speaker: string
  timestamp: string
  text: string
}

/** 構造化トランスクリプトデータ */
export interface TranscriptStructuredData {
  entries: TranscriptEntry[]
}

/** 会議トランスクリプト */
export interface MeetingTranscript {
  id: string
  recurring_meeting_id: string
  meeting_date: string
  google_doc_id: string
  raw_text: string
  structured_data: TranscriptStructuredData | null
  match_confidence: number
  is_auto_linked: boolean
  needs_manual_confirmation: boolean
}

/** トランスクリプト一覧レスポンス */
export interface TranscriptsResponse {
  transcripts: MeetingTranscript[]
}

/** Driveスコープ確認レスポンス */
export interface DriveScopesResponse {
  has_drive_scopes: boolean
}

/** 参加者情報 */
export interface Attendee {
  email: string
  name: string | null
}

/** 定例MTGの頻度 */
export type MeetingFrequency = 'weekly' | 'biweekly' | 'monthly'

/** 定例MTG */
export interface RecurringMeeting {
  id: string
  google_event_id: string
  title: string
  rrule: string
  frequency: MeetingFrequency
  attendees: Attendee[]
  next_occurrence: string
  agent_id: string | null
  created_at: string
  updated_at: string | null
}

/** 定例MTG紐付けリクエスト */
export interface LinkRecurringMeetingRequest {
  recurring_meeting_id: string
}

/** エージェントに紐付けられた定例MTG一覧取得レスポンス */
export type AgentRecurringMeetingsResponse = RecurringMeeting[]

/** 定例MTG紐付けレスポンス */
export interface LinkRecurringMeetingResponse {
  message: string
  recurring_meeting: RecurringMeeting
}

/** 定例MTG紐付け解除レスポンス */
export interface UnlinkRecurringMeetingResponse {
  message: string
}
