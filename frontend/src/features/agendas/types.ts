/**
 * Agenda feature type definitions
 */

export interface Agenda {
  id: string
  agent_id: string
  content: string
  source_note_id: string | null
  generated_at: string
  created_at: string
  updated_at: string | null
}

export interface AgendaGenerateRequest {
  agent_id: string
}

export interface AgendaUpdate {
  content: string
}

export interface DataSourcesInfo {
  has_meeting_note: boolean
  has_slack_messages: boolean
  slack_message_count: number
  dictionary_entry_count: number
}

export interface AgendaGenerateResponse {
  agenda: Agenda
  data_sources: DataSourcesInfo
}
