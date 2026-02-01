-- Update RLS policies for dictionary_entries to support agent_id access
-- TASK-002: RLSポリシー更新 - agent_id経由でのアクセス許可
--
-- 既存のuser_id経由のアクセスは維持し、agent_id経由のアクセスを追加する。
-- agent_id=NULLのエントリは既存方式でアクセス可能。

-- 1. SELECT policy: Allow viewing entries via agent_id
CREATE POLICY "Users can view agent dictionary entries"
ON public.dictionary_entries
FOR SELECT
USING (
  agent_id IS NOT NULL AND
  EXISTS (
    SELECT 1 FROM public.agents
    WHERE agents.id = dictionary_entries.agent_id
    AND agents.user_id = auth.uid()
  )
);

-- 2. INSERT policy: Allow inserting entries via agent_id
CREATE POLICY "Users can insert agent dictionary entries"
ON public.dictionary_entries
FOR INSERT
WITH CHECK (
  agent_id IS NOT NULL AND
  EXISTS (
    SELECT 1 FROM public.agents
    WHERE agents.id = dictionary_entries.agent_id
    AND agents.user_id = auth.uid()
  )
);

-- 3. UPDATE policy: Allow updating entries via agent_id
CREATE POLICY "Users can update agent dictionary entries"
ON public.dictionary_entries
FOR UPDATE
USING (
  agent_id IS NOT NULL AND
  EXISTS (
    SELECT 1 FROM public.agents
    WHERE agents.id = dictionary_entries.agent_id
    AND agents.user_id = auth.uid()
  )
)
WITH CHECK (
  agent_id IS NOT NULL AND
  EXISTS (
    SELECT 1 FROM public.agents
    WHERE agents.id = dictionary_entries.agent_id
    AND agents.user_id = auth.uid()
  )
);

-- 4. DELETE policy: Allow deleting entries via agent_id
CREATE POLICY "Users can delete agent dictionary entries"
ON public.dictionary_entries
FOR DELETE
USING (
  agent_id IS NOT NULL AND
  EXISTS (
    SELECT 1 FROM public.agents
    WHERE agents.id = dictionary_entries.agent_id
    AND agents.user_id = auth.uid()
  )
);
