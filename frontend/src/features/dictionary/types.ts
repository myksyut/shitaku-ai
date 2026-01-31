export interface DictionaryEntry {
  id: string
  canonical_name: string
  description: string | null
  created_at: string
  updated_at: string | null
}

export interface DictionaryEntryCreate {
  canonical_name: string
  description?: string | null
}

export interface DictionaryEntryUpdate {
  canonical_name?: string
  description?: string | null
}
