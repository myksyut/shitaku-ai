import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  deleteGoogleIntegration,
  getGoogleIntegrations,
  getRecurringMeetings,
  startGoogleOAuth,
  syncRecurringMeetings,
} from './api'

export const googleKeys = {
  all: ['google'] as const,
  integrations: () => [...googleKeys.all, 'integrations'] as const,
  recurringMeetings: () => [...googleKeys.all, 'recurringMeetings'] as const,
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

export function useRecurringMeetings() {
  return useQuery({
    queryKey: googleKeys.recurringMeetings(),
    queryFn: getRecurringMeetings,
    select: (data) => data.meetings,
  })
}

export function useSyncRecurringMeetings() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (integrationId: string) => syncRecurringMeetings(integrationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: googleKeys.recurringMeetings() })
    },
  })
}
