import { apiClient } from '../../lib/api-client'
import type {
  DriveScopesResponse,
  GoogleIntegration,
  GoogleOAuthStartResponse,
  LinkRecurringMeetingResponse,
  MeetingTranscript,
  RecurringMeeting,
  TranscriptsResponse,
  UnlinkRecurringMeetingResponse,
} from './types'

const BASE_PATH = '/api/v1/google'

export async function startGoogleOAuth(): Promise<GoogleOAuthStartResponse> {
  return apiClient<GoogleOAuthStartResponse>(`${BASE_PATH}/auth`)
}

export async function getGoogleIntegrations(): Promise<GoogleIntegration[]> {
  return apiClient<GoogleIntegration[]>(`${BASE_PATH}/integrations`)
}

export async function deleteGoogleIntegration(integrationId: string): Promise<void> {
  await apiClient<void>(`${BASE_PATH}/integrations/${integrationId}`, {
    method: 'DELETE',
  })
}

export async function startAdditionalScopes(integrationId: string): Promise<GoogleOAuthStartResponse> {
  return apiClient<GoogleOAuthStartResponse>(`${BASE_PATH}/auth/additional-scopes?integration_id=${integrationId}`)
}

export async function checkDriveScopes(integrationId: string): Promise<DriveScopesResponse> {
  return apiClient<DriveScopesResponse>(`${BASE_PATH}/auth/check-drive-scopes?integration_id=${integrationId}`)
}

export async function getTranscripts(recurringMeetingId: string): Promise<TranscriptsResponse> {
  return apiClient<TranscriptsResponse>(`${BASE_PATH}/transcripts?recurring_meeting_id=${recurringMeetingId}`)
}

export async function syncTranscripts(integrationId: string, recurringMeetingId: string): Promise<TranscriptsResponse> {
  return apiClient<TranscriptsResponse>(
    `${BASE_PATH}/transcripts/sync?integration_id=${integrationId}&recurring_meeting_id=${recurringMeetingId}`,
    { method: 'POST' },
  )
}

export async function linkTranscript(transcriptId: string, recurringMeetingId: string): Promise<MeetingTranscript> {
  return apiClient<MeetingTranscript>(`${BASE_PATH}/transcripts/${transcriptId}/link`, {
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
