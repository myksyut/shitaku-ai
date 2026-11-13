export interface DictionaryEntry {
  id: string
  canonical_name: string
  category: 'person' | 'project' | 'term' | 'customer' | 'abbreviation' | null
  aliases: string[]
  description: string | null
}
export type DictionaryEntryCreate = Omit<DictionaryEntry, 'id'>
export type DictionaryEntryUpdate = Partial<DictionaryEntryCreate>

export const DICTIONARY_CATEGORIES = ['person', 'project', 'term', 'customer', 'abbreviation'] as const
export type DictionaryCategory = (typeof DICTIONARY_CATEGORIES)[number]
export const CATEGORY_LABELS: Record<DictionaryCategory, string> = {
  person: '人名',
  project: 'プロジェクト',
  term: '用語',
  customer: '顧客',
  abbreviation: '略語',
}
