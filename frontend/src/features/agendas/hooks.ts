/**
 * Agenda TanStack Query hooks
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { deleteAgenda, generateAgenda, getAgenda, getAgendas, updateAgenda } from './api'
import type { AgendaGenerateRequest, AgendaUpdate } from './types'

export const agendaKeys = {
  all: ['agendas'] as const,
  lists: () => [...agendaKeys.all, 'list'] as const,
  list: (agentId: string) => [...agendaKeys.lists(), agentId] as const,
  details: () => [...agendaKeys.all, 'detail'] as const,
  detail: (id: string) => [...agendaKeys.details(), id] as const,
}

export function useAgendas(agentId: string, limit?: number) {
  return useQuery({
    queryKey: agendaKeys.list(agentId),
    queryFn: () => getAgendas(agentId, limit),
    enabled: !!agentId,
  })
}

export function useAgenda(id: string) {
  return useQuery({
    queryKey: agendaKeys.detail(id),
    queryFn: () => getAgenda(id),
    enabled: !!id,
  })
}

export function useGenerateAgenda() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: AgendaGenerateRequest) => generateAgenda(data),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: agendaKeys.list(result.agenda.agent_id) })
    },
  })
}

export function useUpdateAgenda() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AgendaUpdate }) => updateAgenda(id, data),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: agendaKeys.detail(result.id) })
      void queryClient.invalidateQueries({ queryKey: agendaKeys.list(result.agent_id) })
    },
  })
}

export function useDeleteAgenda() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => deleteAgenda(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: agendaKeys.lists() })
    },
  })
}
