import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { deleteGoogleIntegration, getGoogleIntegrations, startGoogleOAuth } from './api'

export const googleKeys = {
  all: ['google'] as const,
  integrations: () => [...googleKeys.all, 'integrations'] as const,
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
