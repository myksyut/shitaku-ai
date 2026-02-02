import { apiClient } from '../../lib/api-client'
import type {
  GoogleIntegration,
  GoogleOAuthStartResponse,
  RecurringMeetingsResponse,
  SyncResultResponse,
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

export async function getRecurringMeetings(): Promise<RecurringMeetingsResponse> {
  return apiClient<RecurringMeetingsResponse>(`${BASE_PATH}/calendar/recurring`)
}

export async function syncRecurringMeetings(integrationId: string): Promise<SyncResultResponse> {
  return apiClient<SyncResultResponse>(`${BASE_PATH}/calendar/recurring/sync?integration_id=${integrationId}`, {
    method: 'POST',
  })
}
