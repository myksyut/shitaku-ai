export const DICTIONARY_CATEGORIES = ['person', 'project', 'term', 'customer', 'abbreviation'] as const

export type DictionaryCategory = (typeof DICTIONARY_CATEGORIES)[number]

export const CATEGORY_LABELS: Record<DictionaryCategory, string> = {
  person: '\u4eba\u540d',
  project: '\u30d7\u30ed\u30b8\u30a7\u30af\u30c8',
  term: '\u7528\u8a9e',
  customer: '\u9867\u5ba2',
  abbreviation: '\u7565\u8a9e',
}

export interface DictionaryEntry {
  id: string
  agent_id: string | null
  canonical_name: string
  category: DictionaryCategory | null
  aliases: string[]
  description: string | null
  created_at: string
  updated_at: string | null
}

export interface DictionaryEntryCreate {
  canonical_name: string
  category: DictionaryCategory
  aliases?: string[]
  description?: string | null
}

export interface DictionaryEntryUpdate {
  canonical_name?: string
  category?: DictionaryCategory
  aliases?: string[]
  description?: string | null
}
