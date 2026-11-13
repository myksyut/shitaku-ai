export type SeriesRole = 'creator' | 'member'
export type Resolution = 'reversed' | 'done' | 'dropped' | 'resolved'

export interface OccurrenceSummary {
  id: string
  start_at: string
  is_cancelled: boolean
  has_agenda: boolean
  knowledge_count: number
  topic_count: number
  needs_extraction: boolean
}
export interface SeriesSummary {
  id: string
  title: string
  role: SeriesRole
  next_occurrence: OccurrenceSummary | null
  open_action_items: number
  calendar_sync_error: string | null
}
export interface Attendee {
  email: string
  display_name: string | null
  is_organizer: boolean
}
export interface SlackChannelRef {
  id: string
  name: string
}
export interface SeriesDetail {
  id: string
  title: string
  role: SeriesRole
  rrule: string | null
  attendees: Attendee[]
  occurrences: OccurrenceSummary[]
  settings: { description: string | null; minutes_count: number; slack_message_days: number }
  slack: { integration_id: string; channels: SlackChannelRef[] } | null
  calendar: { synced_at: string; error: string | null; google_connected: boolean }
}
export interface CalendarEventChoice {
  calendar_event_id: string
  title: string
  rrule: string | null
  attendee_count: number
  series_id: string | null
}
export interface ClaimRequest {
  google_integration_id: string
  calendar_event_id: string
}
export interface ClaimResponse {
  outcome: 'created' | 'joined' | 'already_member'
  series: SeriesDetail
}
export interface SeriesSettingsRequest {
  description: string | null
  minutes_count: number
  slack_message_days: number
  slack: { integration_id: string; channel_ids: string[] } | null
}

interface MemoryBase {
  id: string
  body: string
  origin_occurrence_id: string
  origin_start_at: string
  extracted: boolean
}
export type MemoryItem =
  | (MemoryBase & { kind: 'decision'; resolution: 'reversed' | null; closed_at: string | null })
  | (MemoryBase & {
      kind: 'action_item'
      assignee_email: string | null
      due_on: string | null
      resolution: 'done' | 'dropped' | null
      closed_at: string | null
      carry_over: number
    })
  | (MemoryBase & {
      kind: 'open_issue'
      resolution: 'resolved' | 'dropped' | null
      closed_at: string | null
      carry_over: number
    })
export interface TeamMemoryResponse {
  items: MemoryItem[]
}
export type NewMemoryRequest =
  | { kind: 'decision'; body: string; origin_occurrence_id: string }
  | {
      kind: 'action_item'
      body: string
      origin_occurrence_id: string
      assignee_email: string | null
      due_on: string | null
    }
  | { kind: 'open_issue'; body: string; origin_occurrence_id: string }

export interface AgendaTopic {
  id: string
  title: string
  details: string | null
  author_label: string
  is_mine: boolean
  created_at: string
}
export interface Agenda {
  occurrence_id: string
  content: string
  generated_at: string
  updated_at: string
}
export interface KnowledgeSummary {
  id: string
  source: 'upload' | 'meet_transcript'
  title: string | null
  excerpt: string
  created_at: string
}
export interface Knowledge extends KnowledgeSummary {
  text: string
}
export interface OccurrenceDetail {
  occurrence: OccurrenceSummary
  agenda: Agenda | null
  topics: AgendaTopic[]
  knowledge: KnowledgeSummary[]
}
export interface TranscriptCandidate {
  google_doc_id: string
  name: string
  created_at: string
}
export type AddKnowledgeRequest =
  | { source: 'upload'; text: string }
  | { source: 'meet_transcript'; google_doc_id: string }
export interface AgendaSources {
  topics: number
  carried_action_items: number
  open_issues: number
  knowledge: number
  slack_messages: number
  slack_error: string | null
  calendar_error: string | null
}
export interface ExtractionReport {
  created: number
  closed: number
  truncated: boolean
  items: MemoryItem[]
}

export interface AddKnowledgeResponse {
  knowledge: KnowledgeSummary
  normalization_warning: string | null
  replacement_count: number
}
export interface GenerateAgendaResponse {
  agenda: Agenda
  sources: AgendaSources
}
export interface NewTopicRequest {
  title: string
  details?: string
}
