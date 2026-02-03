/**
 * Knowledge TanStack Query hooks
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { deleteKnowledge, getKnowledge, getKnowledgeList, uploadKnowledge } from './api'
import type { KnowledgeCreate } from './types'

export const knowledgeKeys = {
  all: ['knowledge'] as const,
  lists: () => [...knowledgeKeys.all, 'list'] as const,
  list: (agentId: string) => [...knowledgeKeys.lists(), agentId] as const,
  details: () => [...knowledgeKeys.all, 'detail'] as const,
  detail: (id: string) => [...knowledgeKeys.details(), id] as const,
}

export function useKnowledgeList(agentId: string, limit?: number) {
  return useQuery({
    queryKey: knowledgeKeys.list(agentId),
    queryFn: () => getKnowledgeList(agentId, limit),
    enabled: !!agentId,
  })
}

export function useKnowledge(id: string) {
  return useQuery({
    queryKey: knowledgeKeys.detail(id),
    queryFn: () => getKnowledge(id),
    enabled: !!id,
  })
}

export function useUploadKnowledge() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: KnowledgeCreate) => uploadKnowledge(data),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: knowledgeKeys.list(result.knowledge.agent_id) })
    },
  })
}

export function useDeleteKnowledge() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => deleteKnowledge(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: knowledgeKeys.lists() })
    },
  })
}
