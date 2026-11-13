import { apiClient } from '../../lib/api-client'
import type {
  AddKnowledgeRequest,
  AddKnowledgeResponse,
  Agenda,
  AgendaTopic,
  CalendarEventChoice,
  ClaimRequest,
  ClaimResponse,
  ExtractionReport,
  GenerateAgendaResponse,
  Knowledge,
  NewMemoryRequest,
  NewTopicRequest,
  OccurrenceDetail,
  Resolution,
  SeriesDetail,
  SeriesSettingsRequest,
  SeriesSummary,
  TeamMemoryResponse,
  TranscriptCandidate,
} from './types'

const BASE = '/api/v1/series'
const seriesPath = (seriesId: string) => `${BASE}/${encodeURIComponent(seriesId)}`
const occurrencePath = (seriesId: string, occurrenceId: string) =>
  `${seriesPath(seriesId)}/occurrences/${encodeURIComponent(occurrenceId)}`

export async function getMySeries(signal?: AbortSignal) {
  const response = await apiClient<{ series: SeriesSummary[] }>(BASE, { signal })
  return response.series
}

export async function getCalendarEvents(googleIntegrationId: string, signal?: AbortSignal) {
  const params = new URLSearchParams({ google_integration_id: googleIntegrationId })
  const response = await apiClient<{ events: CalendarEventChoice[] }>(`/api/v1/calendar/recurring-events?${params}`, {
    signal,
  })
  return response.events
}

export function claimSeries(request: ClaimRequest) {
  return apiClient<ClaimResponse>(BASE, { method: 'POST', body: JSON.stringify(request) })
}

export function getSeries(seriesId: string, signal?: AbortSignal) {
  return apiClient<SeriesDetail>(seriesPath(seriesId), { signal })
}

export function saveSeriesSettings(seriesId: string, request: SeriesSettingsRequest) {
  return apiClient<SeriesDetail>(`${seriesPath(seriesId)}/settings`, {
    method: 'PUT',
    body: JSON.stringify(request),
  })
}

export function syncSeriesCalendar(seriesId: string) {
  return apiClient<SeriesDetail>(`${seriesPath(seriesId)}/calendar-sync`, { method: 'POST' })
}

export function deleteSeries(seriesId: string) {
  return apiClient<void>(seriesPath(seriesId), { method: 'DELETE' })
}

export function getTeamMemory(seriesId: string, signal?: AbortSignal) {
  return apiClient<TeamMemoryResponse>(`${seriesPath(seriesId)}/memory`, { signal })
}

export function createMemoryItem(seriesId: string, request: NewMemoryRequest) {
  return apiClient<TeamMemoryResponse>(`${seriesPath(seriesId)}/memory`, {
    method: 'POST',
    body: JSON.stringify(request),
  })
}

export function editMemoryItem(seriesId: string, itemId: string, request: NewMemoryRequest) {
  return apiClient<TeamMemoryResponse>(`${seriesPath(seriesId)}/memory/${encodeURIComponent(itemId)}`, {
    method: 'PUT',
    body: JSON.stringify(request),
  })
}

export function setResolution(seriesId: string, itemId: string, resolution: Resolution | null) {
  return apiClient<TeamMemoryResponse>(`${seriesPath(seriesId)}/memory/${encodeURIComponent(itemId)}/resolution`, {
    method: 'PUT',
    body: JSON.stringify({ resolution }),
  })
}

export function deleteMemoryItem(seriesId: string, itemId: string) {
  return apiClient<TeamMemoryResponse>(`${seriesPath(seriesId)}/memory/${encodeURIComponent(itemId)}`, {
    method: 'DELETE',
  })
}

export function getOccurrence(seriesId: string, occurrenceId: string, signal?: AbortSignal) {
  return apiClient<OccurrenceDetail>(occurrencePath(seriesId, occurrenceId), { signal })
}

export function submitTopic(seriesId: string, occurrenceId: string, request: NewTopicRequest) {
  return apiClient<AgendaTopic>(`${occurrencePath(seriesId, occurrenceId)}/topics`, {
    method: 'POST',
    body: JSON.stringify(request),
  })
}

export function deleteTopic(seriesId: string, topicId: string) {
  return apiClient<void>(`${seriesPath(seriesId)}/topics/${encodeURIComponent(topicId)}`, { method: 'DELETE' })
}

export function generateAgenda(seriesId: string, occurrenceId: string) {
  return apiClient<GenerateAgendaResponse>(`${occurrencePath(seriesId, occurrenceId)}/agenda`, { method: 'POST' })
}

export function saveAgenda(seriesId: string, occurrenceId: string, content: string) {
  return apiClient<Agenda>(`${occurrencePath(seriesId, occurrenceId)}/agenda`, {
    method: 'PUT',
    body: JSON.stringify({ content }),
  })
}

export async function getTranscriptCandidates(seriesId: string, occurrenceId: string, signal?: AbortSignal) {
  const response = await apiClient<{ candidates: TranscriptCandidate[] }>(
    `${occurrencePath(seriesId, occurrenceId)}/transcript-candidates`,
    { signal },
  )
  return response.candidates
}

export function addKnowledge(seriesId: string, occurrenceId: string, request: AddKnowledgeRequest) {
  return apiClient<AddKnowledgeResponse>(`${occurrencePath(seriesId, occurrenceId)}/knowledge`, {
    method: 'POST',
    body: JSON.stringify(request),
  })
}

export function extractMemory(seriesId: string, occurrenceId: string) {
  return apiClient<ExtractionReport>(`${occurrencePath(seriesId, occurrenceId)}/extract`, { method: 'POST' })
}

export function getKnowledge(seriesId: string, knowledgeId: string, signal?: AbortSignal) {
  return apiClient<Knowledge>(`${seriesPath(seriesId)}/knowledge/${encodeURIComponent(knowledgeId)}`, { signal })
}

export function deleteKnowledge(seriesId: string, knowledgeId: string) {
  return apiClient<void>(`${seriesPath(seriesId)}/knowledge/${encodeURIComponent(knowledgeId)}`, { method: 'DELETE' })
}
