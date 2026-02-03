-- Rename meeting_notes table to knowledge
-- リファクタリング: 「議事録」→「ナレッジ」への名称変更

-- 1. Drop existing RLS policy
DROP POLICY IF EXISTS "Users can manage own meeting notes" ON public.meeting_notes;

-- 2. Drop existing indexes
DROP INDEX IF EXISTS idx_meeting_notes_agent_id;
DROP INDEX IF EXISTS idx_meeting_notes_user_id;
DROP INDEX IF EXISTS idx_meeting_notes_meeting_date;

-- 3. Rename agendas.source_note_id to source_knowledge_id
ALTER TABLE public.agendas RENAME COLUMN source_note_id TO source_knowledge_id;

-- 4. Rename the table
ALTER TABLE public.meeting_notes RENAME TO knowledge;

-- 5. Recreate indexes with new names
CREATE INDEX IF NOT EXISTS idx_knowledge_agent_id ON public.knowledge(agent_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_user_id ON public.knowledge(user_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_meeting_date ON public.knowledge(agent_id, meeting_date DESC);

-- 6. Recreate RLS policy with new name
CREATE POLICY "Users can manage own knowledge" ON public.knowledge
    FOR ALL USING (auth.uid() = user_id);
