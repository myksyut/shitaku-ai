/**
 * Agent API functions
 */

import { apiClient } from '../../lib/api-client'
import type { Agent, AgentCreate, AgentUpdate } from './types'

const BASE_PATH = '/api/v1/agents'

export async function getAgents(): Promise<Agent[]> {
  return apiClient<Agent[]>(BASE_PATH)
}

export async function getAgent(id: string): Promise<Agent> {
  return apiClient<Agent>(`${BASE_PATH}/${id}`)
}

export async function createAgent(data: AgentCreate): Promise<Agent> {
  return apiClient<Agent>(BASE_PATH, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateAgent(id: string, data: AgentUpdate): Promise<Agent> {
  return apiClient<Agent>(`${BASE_PATH}/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteAgent(id: string): Promise<void> {
  await apiClient<void>(`${BASE_PATH}/${id}`, {
    method: 'DELETE',
  })
}
