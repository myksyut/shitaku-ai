import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  deleteGoogleIntegration,
  getAgentRecurringMeetings,
  getGoogleIntegrations,
  getRecurringMeetings,
  getTranscripts,
  getUnlinkedMeetings,
  linkRecurringMeeting,
  linkTranscript,
  startAdditionalScopes,
  startGoogleOAuth,
  syncRecurringMeetings,
  syncTranscripts,
  unlinkRecurringMeeting,
} from './api'

export const googleKeys = {
  all: ['google'] as const,
  integrations: () => [...googleKeys.all, 'integrations'] as const,
  transcripts: (recurringMeetingId: string) => [...googleKeys.all, 'transcripts', recurringMeetingId] as const,
  recurringMeetings: () => [...googleKeys.all, 'recurringMeetings'] as const,
  unlinkedMeetings: () => [...googleKeys.all, 'unlinkedMeetings'] as const,
  agentMeetings: (agentId: string) => [...googleKeys.all, 'agentMeetings', agentId] as const,
}

export function useGoogleIntegrations() {
  return useQuery({
    queryKey: googleKeys.integrations(),
    queryFn: getGoogleIntegrations,
  })
}

export function useStartGoogleOAuth() {
  return useMutation({
    mutationFn: startGoogleOAuth,
    onSuccess: (data) => {
      window.location.href = data.authorize_url
    },
  })
}

export function useDeleteGoogleIntegration() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (integrationId: string) => deleteGoogleIntegration(integrationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: googleKeys.integrations() })
    },
  })
}

export function useStartAdditionalScopes() {
  return useMutation({
    mutationFn: (integrationId: string) => startAdditionalScopes(integrationId),
    onSuccess: (data) => {
      window.location.href = data.authorize_url
    },
  })
}

const DRIVE_SCOPE = 'https://www.googleapis.com/auth/drive.readonly'
const DOCS_SCOPE = 'https://www.googleapis.com/auth/documents.readonly'

/** integrationのgranted_scopesからDrive/Docsスコープの有無を判定する */
export function hasDriveScopes(grantedScopes: string[]): boolean {
  return grantedScopes.includes(DRIVE_SCOPE) && grantedScopes.includes(DOCS_SCOPE)
}

export function useTranscripts(recurringMeetingId: string | null) {
  return useQuery({
    queryKey: googleKeys.transcripts(recurringMeetingId ?? ''),
    queryFn: () => {
      if (!recurringMeetingId) throw new Error('recurringMeetingId is required')
      return getTranscripts(recurringMeetingId)
    },
    enabled: !!recurringMeetingId,
  })
}

export function useSyncTranscripts() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => syncTranscripts(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: googleKeys.all })
    },
  })
}

export function useLinkTranscript() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ transcriptId, recurringMeetingId }: { transcriptId: string; recurringMeetingId: string }) =>
      linkTranscript(transcriptId, recurringMeetingId),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: googleKeys.transcripts(variables.recurringMeetingId) })
    },
  })
}

// Recurring Meeting hooks
export function useRecurringMeetings() {
  return useQuery({
    queryKey: googleKeys.recurringMeetings(),
    queryFn: getRecurringMeetings,
  })
}

export function useUnlinkedMeetings() {
  return useQuery({
    queryKey: googleKeys.unlinkedMeetings(),
    queryFn: getUnlinkedMeetings,
  })
}

export function useSyncRecurringMeetings() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: syncRecurringMeetings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: googleKeys.recurringMeetings() })
      queryClient.invalidateQueries({ queryKey: googleKeys.unlinkedMeetings() })
    },
  })
}

/** エージェントに紐付けられた定例MTG一覧を取得 */
export function useAgentRecurringMeetings(agentId: string | null) {
  return useQuery({
    queryKey: googleKeys.agentMeetings(agentId ?? ''),
    queryFn: () => {
      if (!agentId) throw new Error('agentId is required')
      return getAgentRecurringMeetings(agentId)
    },
    enabled: !!agentId,
  })
}

/** 定例MTGをエージェントに紐付け */
export function useLinkRecurringMeeting() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ agentId, recurringMeetingId }: { agentId: string; recurringMeetingId: string }) =>
      linkRecurringMeeting(agentId, recurringMeetingId),
    onSuccess: (_, { agentId }) => {
      queryClient.invalidateQueries({ queryKey: googleKeys.agentMeetings(agentId) })
      queryClient.invalidateQueries({ queryKey: googleKeys.unlinkedMeetings() })
      queryClient.invalidateQueries({ queryKey: googleKeys.recurringMeetings() })
    },
  })
}

/** 定例MTGとエージェントの紐付けを解除 */
export function useUnlinkRecurringMeeting() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ agentId, meetingId }: { agentId: string; meetingId: string }) =>
      unlinkRecurringMeeting(agentId, meetingId),
    onSuccess: (_, { agentId }) => {
      queryClient.invalidateQueries({ queryKey: googleKeys.agentMeetings(agentId) })
      queryClient.invalidateQueries({ queryKey: googleKeys.unlinkedMeetings() })
      queryClient.invalidateQueries({ queryKey: googleKeys.recurringMeetings() })
    },
  })
}
