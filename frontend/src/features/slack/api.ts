import { apiClient } from '../../lib/api-client'
import type { SlackChannel, SlackIntegration, SlackMessage, SlackOAuthStartResponse } from './types'

const BASE_PATH = '/api/v1/slack'

export async function startSlackOAuth(): Promise<SlackOAuthStartResponse> {
  return apiClient<SlackOAuthStartResponse>(`${BASE_PATH}/auth`)
}

export async function getSlackIntegrations(): Promise<SlackIntegration[]> {
  return apiClient<SlackIntegration[]>(`${BASE_PATH}/integrations`)
}

export async function deleteSlackIntegration(integrationId: string): Promise<void> {
  await apiClient<void>(`${BASE_PATH}/integrations/${integrationId}`, {
    method: 'DELETE',
  })
}

export async function getSlackChannels(integrationId: string): Promise<SlackChannel[]> {
  return apiClient<SlackChannel[]>(`${BASE_PATH}/integrations/${integrationId}/channels`)
}

export async function getSlackMessages(
  integrationId: string,
  channelId: string,
  oldest: string,
  latest?: string,
): Promise<SlackMessage[]> {
  const params = new URLSearchParams({ oldest })
  if (latest) {
    params.append('latest', latest)
  }
  return apiClient<SlackMessage[]>(
    `${BASE_PATH}/integrations/${integrationId}/channels/${channelId}/messages?${params.toString()}`,
  )
}
