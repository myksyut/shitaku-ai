import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createAgentDictionaryEntry,
  createDictionaryEntry,
  deleteAgentDictionaryEntry,
  deleteDictionaryEntry,
  getAgentDictionaryEntries,
  getDictionaryEntries,
  getDictionaryEntry,
  updateAgentDictionaryEntry,
  updateDictionaryEntry,
} from './api'
import type { DictionaryEntryCreate, DictionaryEntryUpdate } from './types'

export const dictionaryKeys = {
  all: ['dictionary'] as const,
  lists: () => [...dictionaryKeys.all, 'list'] as const,
  list: () => [...dictionaryKeys.lists()] as const,
  details: () => [...dictionaryKeys.all, 'detail'] as const,
  detail: (id: string) => [...dictionaryKeys.details(), id] as const,
}

export function useDictionaryEntries() {
  return useQuery({
    queryKey: dictionaryKeys.list(),
    queryFn: getDictionaryEntries,
  })
}

export function useDictionaryEntry(id: string) {
  return useQuery({
    queryKey: dictionaryKeys.detail(id),
    queryFn: () => getDictionaryEntry(id),
    enabled: !!id,
  })
}

export function useCreateDictionaryEntry() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: DictionaryEntryCreate) => createDictionaryEntry(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dictionaryKeys.lists() })
    },
  })
}

export function useUpdateDictionaryEntry() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: DictionaryEntryUpdate }) => updateDictionaryEntry(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: dictionaryKeys.lists() })
      queryClient.invalidateQueries({ queryKey: dictionaryKeys.detail(id) })
    },
  })
}

export function useDeleteDictionaryEntry() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => deleteDictionaryEntry(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dictionaryKeys.lists() })
    },
  })
}

// --- Agent-specific Dictionary Hooks ---

export const agentDictionaryKeys = {
  all: ['agent-dictionary'] as const,
  list: (agentId: string) => [...agentDictionaryKeys.all, 'list', agentId] as const,
}

export function useAgentDictionaryEntries(agentId: string) {
  return useQuery({
    queryKey: agentDictionaryKeys.list(agentId),
    queryFn: () => getAgentDictionaryEntries(agentId),
    enabled: !!agentId,
  })
}

export function useCreateAgentDictionaryEntry(agentId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: DictionaryEntryCreate) => createAgentDictionaryEntry(agentId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: agentDictionaryKeys.list(agentId),
      })
    },
  })
}

export function useUpdateAgentDictionaryEntry(agentId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ entryId, data }: { entryId: string; data: DictionaryEntryUpdate }) =>
      updateAgentDictionaryEntry(agentId, entryId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: agentDictionaryKeys.list(agentId),
      })
    },
  })
}

export function useDeleteAgentDictionaryEntry(agentId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (entryId: string) => deleteAgentDictionaryEntry(agentId, entryId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: agentDictionaryKeys.list(agentId),
      })
    },
  })
}
