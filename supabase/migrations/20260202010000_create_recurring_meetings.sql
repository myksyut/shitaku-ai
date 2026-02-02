-- 定例MTGテーブル
-- Phase 1-2: Google Workspace連携 - Calendar API定例MTG検出

CREATE TABLE public.recurring_meetings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    google_event_id TEXT NOT NULL,
    title TEXT NOT NULL,
    rrule TEXT NOT NULL,
    frequency TEXT NOT NULL CHECK (frequency IN ('weekly', 'biweekly', 'monthly')),
    attendees JSONB NOT NULL DEFAULT '[]',
    next_occurrence TIMESTAMPTZ NOT NULL,
    agent_id UUID REFERENCES public.agents(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    UNIQUE(user_id, google_event_id)
);

CREATE INDEX idx_recurring_meetings_user_id ON public.recurring_meetings(user_id);
CREATE INDEX idx_recurring_meetings_next_occurrence ON public.recurring_meetings(next_occurrence);

ALTER TABLE public.recurring_meetings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own recurring meetings" ON public.recurring_meetings
    FOR ALL USING (auth.uid() = user_id);
