import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { seriesKeys } from '../series/hooks'
import { deleteGoogleIntegration, getGoogleIntegrations, startAdditionalScopes, startGoogleOAuth } from './api'

export const googleKeys = {
  all: ['google'] as const,
  integrations: () => [...googleKeys.all, 'integrations'] as const,
}

export function useGoogleIntegrations() {
  return useQuery({ queryKey: googleKeys.integrations(), queryFn: getGoogleIntegrations })
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
  const client = useQueryClient()
  return useMutation({
    mutationFn: deleteGoogleIntegration,
    onSuccess: () =>
      Promise.all([
        client.invalidateQueries({ queryKey: googleKeys.integrations() }),
        client.invalidateQueries({ queryKey: seriesKeys.all }),
      ]),
  })
}

export function useStartAdditionalScopes() {
  return useMutation({
    mutationFn: startAdditionalScopes,
    onSuccess: (data) => {
      window.location.href = data.authorize_url
    },
  })
}
