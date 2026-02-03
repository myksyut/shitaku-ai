/**
 * Agenda feature type definitions
 */

export interface Agenda {
  id: string
  agent_id: string
  content: string
  source_knowledge_id: string | null
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
  has_knowledge: boolean
  has_slack_messages: boolean
  slack_message_count: number
  dictionary_entry_count: number
  has_transcripts: boolean
  transcript_count: number
  slack_error: string | null
}

export interface AgendaGenerateResponse {
  agenda: Agenda
  data_sources: DataSourcesInfo
}
