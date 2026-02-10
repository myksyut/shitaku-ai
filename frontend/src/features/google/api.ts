import { apiClient } from '../../lib/api-client'
import type {
  GoogleIntegration,
  GoogleOAuthStartResponse,
  LinkRecurringMeetingResponse,
  MeetingTranscript,
  RecurringMeeting,
  SyncProviderTokenRequest,
  SyncProviderTokenResponse,
  SyncResultResponse,
  UnlinkRecurringMeetingResponse,
} from './types'

const BASE_PATH = '/api/v1/google'

export async function startGoogleOAuth(): Promise<GoogleOAuthStartResponse> {
  const params = new URLSearchParams({ redirect_origin: window.location.origin })
  return apiClient<GoogleOAuthStartResponse>(`${BASE_PATH}/auth?${params.toString()}`)
}

export async function getGoogleIntegrations(): Promise<GoogleIntegration[]> {
  return apiClient<GoogleIntegration[]>(`${BASE_PATH}/integrations`)
}

export async function deleteGoogleIntegration(integrationId: string): Promise<void> {
  await apiClient<void>(`${BASE_PATH}/integrations/${integrationId}`, {
    method: 'DELETE',
  })
}

export async function syncProviderToken(request: SyncProviderTokenRequest): Promise<SyncProviderTokenResponse> {
  return apiClient<SyncProviderTokenResponse>(`${BASE_PATH}/sync-token`, {
    method: 'POST',
    body: JSON.stringify(request),
  })
}

export async function startAdditionalScopes(integrationId: string): Promise<GoogleOAuthStartResponse> {
  const params = new URLSearchParams({
    integration_id: integrationId,
    redirect_origin: window.location.origin,
  })
  return apiClient<GoogleOAuthStartResponse>(`${BASE_PATH}/auth/additional-scopes?${params.toString()}`)
}

// Transcript API functions
const TRANSCRIPTS_PATH = '/api/v1/transcripts'

export async function getTranscripts(recurringMeetingId: string): Promise<MeetingTranscript[]> {
  return apiClient<MeetingTranscript[]>(`${TRANSCRIPTS_PATH}?recurring_meeting_id=${recurringMeetingId}`)
}

export async function syncTranscripts(): Promise<SyncResultResponse> {
  return apiClient<SyncResultResponse>(`${TRANSCRIPTS_PATH}/sync`, { method: 'POST' })
}

export async function linkTranscript(transcriptId: string, recurringMeetingId: string): Promise<MeetingTranscript> {
  return apiClient<MeetingTranscript>(`${TRANSCRIPTS_PATH}/${transcriptId}/link`, {
    method: 'POST',
    body: JSON.stringify({ recurring_meeting_id: recurringMeetingId }),
  })
}

// Calendar API functions
const CALENDAR_PATH = '/api/v1/calendar'

export async function getRecurringMeetings(): Promise<RecurringMeeting[]> {
  return apiClient<RecurringMeeting[]>(`${CALENDAR_PATH}/recurring`)
}

export async function getUnlinkedMeetings(): Promise<RecurringMeeting[]> {
  return apiClient<RecurringMeeting[]>(`${CALENDAR_PATH}/recurring/unlinked`)
}

export async function syncRecurringMeetings(): Promise<RecurringMeeting[]> {
  return apiClient<RecurringMeeting[]>(`${CALENDAR_PATH}/sync`, {
    method: 'POST',
  })
}

// Agent recurring meeting API functions
const AGENTS_PATH = '/api/v1/agents'

/** エージェントに紐付けられた定例MTG一覧を取得 */
export async function getAgentRecurringMeetings(agentId: string): Promise<RecurringMeeting[]> {
  return apiClient<RecurringMeeting[]>(`${AGENTS_PATH}/${agentId}/recurring-meetings`)
}

/** 定例MTGをエージェントに紐付け */
export async function linkRecurringMeeting(
  agentId: string,
  recurringMeetingId: string,
): Promise<LinkRecurringMeetingResponse> {
  return apiClient<LinkRecurringMeetingResponse>(`${AGENTS_PATH}/${agentId}/recurring-meetings`, {
    method: 'POST',
    body: JSON.stringify({ recurring_meeting_id: recurringMeetingId }),
  })
}

/** 定例MTGとエージェントの紐付けを解除 */
export async function unlinkRecurringMeeting(
  agentId: string,
  meetingId: string,
): Promise<UnlinkRecurringMeetingResponse> {
  return apiClient<UnlinkRecurringMeetingResponse>(`${AGENTS_PATH}/${agentId}/recurring-meetings/${meetingId}`, {
    method: 'DELETE',
  })
}
