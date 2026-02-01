/**
 * MeetingNote feature type definitions
 */

export interface MeetingNote {
  id: string
  agent_id: string
  original_text: string
  normalized_text: string
  meeting_date: string
  created_at: string
  is_normalized: boolean
}

export interface MeetingNoteCreate {
  agent_id: string
  text: string
  meeting_date: string
}

export interface MeetingNoteUploadResponse {
  note: MeetingNote
  normalization_warning: string | null
  replacement_count: number
}
