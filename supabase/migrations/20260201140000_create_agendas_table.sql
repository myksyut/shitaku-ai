-- Create agendas table for agenda auto-generation
-- Phase 6: アジェンダ自動生成機能

CREATE TABLE IF NOT EXISTS public.agendas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES public.agents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    source_note_id UUID REFERENCES public.meeting_notes(id) ON DELETE SET NULL,
    generated_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_agendas_agent_id ON public.agendas(agent_id);
CREATE INDEX IF NOT EXISTS idx_agendas_user_id ON public.agendas(user_id);
CREATE INDEX IF NOT EXISTS idx_agendas_generated_at ON public.agendas(agent_id, generated_at DESC);

-- Enable Row Level Security
ALTER TABLE public.agendas ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can only manage their own agendas
CREATE POLICY "Users can manage own agendas" ON public.agendas
    FOR ALL USING (auth.uid() = user_id);
