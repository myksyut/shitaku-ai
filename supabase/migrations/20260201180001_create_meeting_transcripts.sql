-- meeting_transcripts テーブル
-- Google Meetトランスクリプトを保存

CREATE TABLE public.meeting_transcripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recurring_meeting_id UUID NOT NULL REFERENCES public.recurring_meetings(id) ON DELETE CASCADE,
    meeting_date TIMESTAMPTZ NOT NULL,
    google_doc_id TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    structured_data JSONB,
    match_confidence REAL NOT NULL DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(recurring_meeting_id, google_doc_id)
);

-- RLSポリシー（親テーブル経由でuser_id検証）
ALTER TABLE public.meeting_transcripts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own meeting transcripts" ON public.meeting_transcripts
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.recurring_meetings rm
            WHERE rm.id = meeting_transcripts.recurring_meeting_id
            AND rm.user_id = auth.uid()
        )
    );

-- インデックス
CREATE INDEX idx_meeting_transcripts_recurring_meeting_id ON public.meeting_transcripts(recurring_meeting_id);
CREATE INDEX idx_meeting_transcripts_meeting_date ON public.meeting_transcripts(meeting_date);
