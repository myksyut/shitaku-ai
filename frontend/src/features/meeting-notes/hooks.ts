/**
 * MeetingNote TanStack Query hooks
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { deleteMeetingNote, getMeetingNote, getMeetingNotes, uploadMeetingNote } from './api'
import type { MeetingNoteCreate } from './types'

export const meetingNoteKeys = {
  all: ['meeting-notes'] as const,
  lists: () => [...meetingNoteKeys.all, 'list'] as const,
  list: (agentId: string) => [...meetingNoteKeys.lists(), agentId] as const,
  details: () => [...meetingNoteKeys.all, 'detail'] as const,
  detail: (id: string) => [...meetingNoteKeys.details(), id] as const,
}

export function useMeetingNotes(agentId: string, limit?: number) {
  return useQuery({
    queryKey: meetingNoteKeys.list(agentId),
    queryFn: () => getMeetingNotes(agentId, limit),
    enabled: !!agentId,
  })
}

export function useMeetingNote(id: string) {
  return useQuery({
    queryKey: meetingNoteKeys.detail(id),
    queryFn: () => getMeetingNote(id),
    enabled: !!id,
  })
}

export function useUploadMeetingNote() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: MeetingNoteCreate) => uploadMeetingNote(data),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: meetingNoteKeys.list(result.note.agent_id) })
    },
  })
}

export function useDeleteMeetingNote() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => deleteMeetingNote(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: meetingNoteKeys.lists() })
    },
  })
}
