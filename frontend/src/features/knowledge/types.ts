/**
 * Knowledge feature type definitions
 */

export interface Knowledge {
  id: string
  agent_id: string
  original_text: string
  normalized_text: string
  meeting_date: string
  created_at: string
  is_normalized: boolean
}

export interface KnowledgeCreate {
  agent_id: string
  text: string
}

export interface KnowledgeUploadResponse {
  knowledge: Knowledge
  normalization_warning: string | null
  replacement_count: number
}
