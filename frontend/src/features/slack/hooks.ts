import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  deleteSlackIntegration,
  getSlackChannels,
  getSlackIntegrations,
  getSlackMessages,
  startSlackOAuth,
} from './api'

export const slackKeys = {
  all: ['slack'] as const,
  integrations: () => [...slackKeys.all, 'integrations'] as const,
  channels: (integrationId: string) => [...slackKeys.all, 'channels', integrationId] as const,
  messages: (integrationId: string, channelId: string) =>
    [...slackKeys.all, 'messages', integrationId, channelId] as const,
}

export function useSlackIntegrations() {
  return useQuery({
    queryKey: slackKeys.integrations(),
    queryFn: getSlackIntegrations,
  })
}

export function useSlackChannels(integrationId: string) {
  return useQuery({
    queryKey: slackKeys.channels(integrationId),
    queryFn: () => getSlackChannels(integrationId),
    enabled: !!integrationId,
  })
}

export function useSlackMessages(integrationId: string, channelId: string, oldest: string, latest?: string) {
  return useQuery({
    queryKey: slackKeys.messages(integrationId, channelId),
    queryFn: () => getSlackMessages(integrationId, channelId, oldest, latest),
    enabled: !!integrationId && !!channelId && !!oldest,
  })
}

export function useStartSlackOAuth() {
  return useMutation({
    mutationFn: startSlackOAuth,
    onSuccess: (data) => {
      window.location.href = data.authorize_url
    },
  })
}

export function useDeleteSlackIntegration() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (integrationId: string) => deleteSlackIntegration(integrationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: slackKeys.integrations() })
    },
  })
}
