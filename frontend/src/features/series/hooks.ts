import { type QueryClient, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as api from './api'
import type {
  AddKnowledgeRequest,
  MemoryItem,
  NewMemoryRequest,
  NewTopicRequest,
  Resolution,
  SeriesSettingsRequest,
  TeamMemoryResponse,
} from './types'

export const seriesKeys = {
  all: ['series'] as const,
  list: () => [...seriesKeys.all, 'list'] as const,
  detail: (seriesId: string) => [...seriesKeys.all, 'detail', seriesId] as const,
  memory: (seriesId: string) => [...seriesKeys.detail(seriesId), 'memory'] as const,
  occurrence: (seriesId: string, occurrenceId: string) =>
    [...seriesKeys.detail(seriesId), 'occurrence', occurrenceId] as const,
  transcriptCandidates: (seriesId: string, occurrenceId: string) =>
    [...seriesKeys.occurrence(seriesId, occurrenceId), 'transcript-candidates'] as const,
  knowledge: (seriesId: string, knowledgeId: string) =>
    [...seriesKeys.detail(seriesId), 'knowledge', knowledgeId] as const,
  dictionary: (seriesId: string) => [...seriesKeys.detail(seriesId), 'dictionary'] as const,
}
export const calendarKeys = {
  events: (googleIntegrationId: string) => ['calendar', 'recurring-events', googleIntegrationId] as const,
}

export function invalidateSeries(queryClient: QueryClient, seriesId: string) {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: seriesKeys.detail(seriesId) }),
    queryClient.invalidateQueries({ queryKey: seriesKeys.list() }),
  ])
}

async function updateBoard(queryClient: QueryClient, seriesId: string, board: TeamMemoryResponse) {
  await invalidateSeries(queryClient, seriesId)
  queryClient.setQueryData(seriesKeys.memory(seriesId), board)
}

export function useMySeries() {
  return useQuery({ queryKey: seriesKeys.list(), queryFn: ({ signal }) => api.getMySeries(signal) })
}

export function useCalendarEvents(googleIntegrationId: string | null) {
  return useQuery({
    queryKey: calendarKeys.events(googleIntegrationId ?? ''),
    queryFn: ({ signal }) => api.getCalendarEvents(googleIntegrationId ?? '', signal),
    enabled: googleIntegrationId !== null,
  })
}

export function useClaimSeries() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: api.claimSeries,
    onSuccess: async ({ series }, request) => {
      await invalidateSeries(client, series.id)
      client.setQueryData(seriesKeys.detail(series.id), series)
      await client.invalidateQueries({ queryKey: calendarKeys.events(request.google_integration_id) })
    },
  })
}

export function useSeries(seriesId: string) {
  return useQuery({
    queryKey: seriesKeys.detail(seriesId),
    queryFn: ({ signal }) => api.getSeries(seriesId, signal),
    enabled: !!seriesId,
  })
}

export function useSaveSeriesSettings(seriesId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (request: SeriesSettingsRequest) => api.saveSeriesSettings(seriesId, request),
    onSuccess: () => invalidateSeries(client, seriesId),
  })
}

export function useSyncSeriesCalendar(seriesId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: () => api.syncSeriesCalendar(seriesId),
    onSuccess: () => invalidateSeries(client, seriesId),
  })
}

export function useDeleteSeries() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: api.deleteSeries,
    onSuccess: (_, seriesId) => invalidateSeries(client, seriesId),
  })
}

export function useTeamMemory(seriesId: string) {
  return useQuery({
    queryKey: seriesKeys.memory(seriesId),
    queryFn: ({ signal }) => api.getTeamMemory(seriesId, signal),
    enabled: !!seriesId,
  })
}

export function useCreateMemoryItem(seriesId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (request: NewMemoryRequest) => api.createMemoryItem(seriesId, request),
    onSuccess: (board) => updateBoard(client, seriesId, board),
  })
}

export function useEditMemoryItem(seriesId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: ({ itemId, request }: { itemId: string; request: NewMemoryRequest }) =>
      api.editMemoryItem(seriesId, itemId, request),
    onSuccess: (board) => updateBoard(client, seriesId, board),
  })
}

function optimisticResolution(item: MemoryItem, resolution: Resolution | null): MemoryItem {
  const closed_at = resolution === null ? null : new Date().toISOString()
  switch (item.kind) {
    case 'decision':
      return resolution === null || resolution === 'reversed' ? { ...item, resolution, closed_at } : item
    case 'action_item':
      return resolution === null || resolution === 'done' || resolution === 'dropped'
        ? { ...item, resolution, closed_at }
        : item
    case 'open_issue':
      return resolution === null || resolution === 'resolved' || resolution === 'dropped'
        ? { ...item, resolution, closed_at }
        : item
  }
}

export function useSetResolution(seriesId: string) {
  const client = useQueryClient()
  const key = seriesKeys.memory(seriesId)
  return useMutation({
    mutationFn: ({ itemId, resolution }: { itemId: string; resolution: Resolution | null }) =>
      api.setResolution(seriesId, itemId, resolution),
    onMutate: async ({ itemId, resolution }) => {
      await client.cancelQueries({ queryKey: key })
      const previous = client.getQueryData<TeamMemoryResponse>(key)
      if (previous) {
        client.setQueryData<TeamMemoryResponse>(key, {
          items: previous.items.map((item) => (item.id === itemId ? optimisticResolution(item, resolution) : item)),
        })
      }
      return { previous }
    },
    onError: (_, __, context) => {
      if (context?.previous) client.setQueryData(key, context.previous)
    },
    onSuccess: (board) => updateBoard(client, seriesId, board),
  })
}

export function useDeleteMemoryItem(seriesId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (itemId: string) => api.deleteMemoryItem(seriesId, itemId),
    onSuccess: (board) => updateBoard(client, seriesId, board),
  })
}

export function useOccurrence(seriesId: string, occurrenceId: string) {
  return useQuery({
    queryKey: seriesKeys.occurrence(seriesId, occurrenceId),
    queryFn: ({ signal }) => api.getOccurrence(seriesId, occurrenceId, signal),
    enabled: !!seriesId && !!occurrenceId,
  })
}

export function useSubmitTopic(seriesId: string, occurrenceId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (request: NewTopicRequest) => api.submitTopic(seriesId, occurrenceId, request),
    onSuccess: () => invalidateSeries(client, seriesId),
  })
}

export function useDeleteTopic(seriesId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (topicId: string) => api.deleteTopic(seriesId, topicId),
    onSuccess: () => invalidateSeries(client, seriesId),
  })
}

export function useGenerateAgenda(seriesId: string, occurrenceId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: () => api.generateAgenda(seriesId, occurrenceId),
    onSuccess: () => invalidateSeries(client, seriesId),
  })
}

export function useSaveAgenda(seriesId: string, occurrenceId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (content: string) => api.saveAgenda(seriesId, occurrenceId, content),
    onSuccess: () => invalidateSeries(client, seriesId),
  })
}

export function useTranscriptCandidates(seriesId: string, occurrenceId: string, enabled: boolean) {
  return useQuery({
    queryKey: seriesKeys.transcriptCandidates(seriesId, occurrenceId),
    queryFn: ({ signal }) => api.getTranscriptCandidates(seriesId, occurrenceId, signal),
    enabled: enabled && !!seriesId && !!occurrenceId,
  })
}

export function useAddKnowledge(seriesId: string, occurrenceId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (request: AddKnowledgeRequest) => api.addKnowledge(seriesId, occurrenceId, request),
    onSuccess: () => invalidateSeries(client, seriesId),
  })
}

export function useExtractMemory(seriesId: string, occurrenceId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: () => api.extractMemory(seriesId, occurrenceId),
    onSuccess: (report) => updateBoard(client, seriesId, { items: report.items }),
  })
}

export function useKnowledge(seriesId: string, knowledgeId: string) {
  return useQuery({
    queryKey: seriesKeys.knowledge(seriesId, knowledgeId),
    queryFn: ({ signal }) => api.getKnowledge(seriesId, knowledgeId, signal),
    enabled: !!seriesId && !!knowledgeId,
  })
}

export function useDeleteKnowledge(seriesId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (knowledgeId: string) => api.deleteKnowledge(seriesId, knowledgeId),
    onSuccess: () => invalidateSeries(client, seriesId),
  })
}
