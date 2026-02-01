-- Create meeting_notes table for meeting note management
-- Phase 4: 議事録アップロード + 正規化

CREATE TABLE IF NOT EXISTS public.meeting_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES public.agents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    original_text TEXT NOT NULL,
    normalized_text TEXT NOT NULL,
    meeting_date TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_meeting_notes_agent_id ON public.meeting_notes(agent_id);
CREATE INDEX IF NOT EXISTS idx_meeting_notes_user_id ON public.meeting_notes(user_id);
CREATE INDEX IF NOT EXISTS idx_meeting_notes_meeting_date ON public.meeting_notes(agent_id, meeting_date DESC);

-- Enable Row Level Security
ALTER TABLE public.meeting_notes ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can only manage their own meeting notes
CREATE POLICY "Users can manage own meeting notes" ON public.meeting_notes
    FOR ALL USING (auth.uid() = user_id);
