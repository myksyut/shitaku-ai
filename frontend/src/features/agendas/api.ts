/**
 * Agenda API functions
 */

import { apiClient } from '../../lib/api-client'
import type { Agenda, AgendaGenerateRequest, AgendaGenerateResponse, AgendaUpdate } from './types'

const BASE_PATH = '/api/v1/agendas'

export async function generateAgenda(data: AgendaGenerateRequest): Promise<AgendaGenerateResponse> {
  return apiClient<AgendaGenerateResponse>(`${BASE_PATH}/generate`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function getAgendas(agentId: string, limit?: number): Promise<Agenda[]> {
  const params = new URLSearchParams({ agent_id: agentId })
  if (limit) {
    params.append('limit', String(limit))
  }
  return apiClient<Agenda[]>(`${BASE_PATH}?${params.toString()}`)
}

export async function getAgenda(id: string): Promise<Agenda> {
  return apiClient<Agenda>(`${BASE_PATH}/${id}`)
}

export async function updateAgenda(id: string, data: AgendaUpdate): Promise<Agenda> {
  return apiClient<Agenda>(`${BASE_PATH}/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteAgenda(id: string): Promise<void> {
  await apiClient<void>(`${BASE_PATH}/${id}`, {
    method: 'DELETE',
  })
}
