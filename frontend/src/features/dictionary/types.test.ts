import { describe, expect, it } from 'vitest'
import {
  CATEGORY_LABELS,
  DICTIONARY_CATEGORIES,
  type DictionaryCategory,
  type DictionaryEntry,
  type DictionaryEntryCreate,
  type DictionaryEntryUpdate,
} from './types'

describe('Dictionary Types', () => {
  describe('DICTIONARY_CATEGORIES', () => {
    it('should contain all 5 categories', () => {
      expect(DICTIONARY_CATEGORIES).toHaveLength(5)
      expect(DICTIONARY_CATEGORIES).toContain('person')
      expect(DICTIONARY_CATEGORIES).toContain('project')
      expect(DICTIONARY_CATEGORIES).toContain('term')
      expect(DICTIONARY_CATEGORIES).toContain('customer')
      expect(DICTIONARY_CATEGORIES).toContain('abbreviation')
    })
  })

  describe('CATEGORY_LABELS', () => {
    it('should have Japanese labels for all categories', () => {
      expect(CATEGORY_LABELS.person).toBe('\u4eba\u540d')
      expect(CATEGORY_LABELS.project).toBe('\u30d7\u30ed\u30b8\u30a7\u30af\u30c8')
      expect(CATEGORY_LABELS.term).toBe('\u7528\u8a9e')
      expect(CATEGORY_LABELS.customer).toBe('\u9867\u5ba2')
      expect(CATEGORY_LABELS.abbreviation).toBe('\u7565\u8a9e')
    })
  })

  describe('DictionaryEntry type', () => {
    it('should have all required fields including agent_id, category, aliases', () => {
      const entry: DictionaryEntry = {
        id: 'test-id',
        agent_id: 'agent-123',
        canonical_name: 'Test Entry',
        category: 'person',
        aliases: ['alias1', 'alias2'],
        description: 'Test description',
        created_at: '2026-01-31T00:00:00Z',
        updated_at: '2026-01-31T01:00:00Z',
      }

      expect(entry.id).toBe('test-id')
      expect(entry.agent_id).toBe('agent-123')
      expect(entry.canonical_name).toBe('Test Entry')
      expect(entry.category).toBe('person')
      expect(entry.aliases).toEqual(['alias1', 'alias2'])
      expect(entry.description).toBe('Test description')
    })

    it('should allow null for agent_id, category, description', () => {
      const entry: DictionaryEntry = {
        id: 'test-id',
        agent_id: null,
        canonical_name: 'Test Entry',
        category: null,
        aliases: [],
        description: null,
        created_at: '2026-01-31T00:00:00Z',
        updated_at: null,
      }

      expect(entry.agent_id).toBeNull()
      expect(entry.category).toBeNull()
      expect(entry.description).toBeNull()
    })
  })

  describe('DictionaryEntryCreate type', () => {
    it('should require canonical_name and category', () => {
      const createData: DictionaryEntryCreate = {
        canonical_name: 'New Entry',
        category: 'project',
      }

      expect(createData.canonical_name).toBe('New Entry')
      expect(createData.category).toBe('project')
    })

    it('should allow optional aliases and description', () => {
      const createData: DictionaryEntryCreate = {
        canonical_name: 'New Entry',
        category: 'term',
        aliases: ['alias1'],
        description: 'Optional description',
      }

      expect(createData.aliases).toEqual(['alias1'])
      expect(createData.description).toBe('Optional description')
    })
  })

  describe('DictionaryEntryUpdate type', () => {
    it('should allow partial updates', () => {
      const updateData: DictionaryEntryUpdate = {
        canonical_name: 'Updated Name',
      }

      expect(updateData.canonical_name).toBe('Updated Name')
      expect(updateData.category).toBeUndefined()
    })

    it('should allow updating all fields', () => {
      const updateData: DictionaryEntryUpdate = {
        canonical_name: 'Updated Name',
        category: 'customer',
        aliases: ['new-alias'],
        description: 'Updated description',
      }

      expect(updateData.canonical_name).toBe('Updated Name')
      expect(updateData.category).toBe('customer')
      expect(updateData.aliases).toEqual(['new-alias'])
      expect(updateData.description).toBe('Updated description')
    })
  })

  describe('DictionaryCategory type', () => {
    it('should accept valid category values', () => {
      const categories: DictionaryCategory[] = ['person', 'project', 'term', 'customer', 'abbreviation']

      expect(categories).toHaveLength(5)
    })
  })
})
