-- Add agent_id, category, aliases columns to dictionary_entries
-- TASK-001: Migration for agent-based dictionary management

-- Add columns
ALTER TABLE public.dictionary_entries
  ADD COLUMN agent_id UUID REFERENCES public.agents(id) ON DELETE CASCADE,
  ADD COLUMN category VARCHAR(50),
  ADD COLUMN aliases TEXT[] NOT NULL DEFAULT '{}';

-- Create index for agent_id
CREATE INDEX idx_dictionary_entries_agent_id ON public.dictionary_entries(agent_id);

-- Add check constraint for category (for data integrity)
ALTER TABLE public.dictionary_entries
  ADD CONSTRAINT chk_dictionary_category
  CHECK (category IS NULL OR category IN ('person', 'project', 'term', 'customer', 'abbreviation'));
