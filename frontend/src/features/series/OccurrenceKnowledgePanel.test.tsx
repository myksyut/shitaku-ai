import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse, http } from 'msw'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { API, actionItem, occurrence, renderPage, series, server } from '../../test/series'
import { OccurrencePage } from './OccurrencePage'

describe('meeting minutes extraction', () => {
  it('saves minutes before extraction, keeps failed extraction retryable, and reports truncation', async () => {
    let stored = false
    let extracted = false
    let attempts = 0
    const calls: string[] = []
    const knowledge = {
      id: 'knowledge-1',
      source: 'upload',
      title: null,
      excerpt: '議事録の内容',
      created_at: '2026-11-13T10:00:00Z',
    }
    server.use(
      http.get(`${API}/series/series-1`, () => HttpResponse.json({ ...series, role: 'creator' })),
      http.get(`${API}/series/series-1/occurrences/occurrence-1`, () =>
        HttpResponse.json({
          ...occurrence,
          knowledge: stored ? [knowledge] : [],
          occurrence: {
            ...occurrence.occurrence,
            start_at: '2020-01-01T10:00:00Z',
            knowledge_count: stored ? 1 : 0,
            needs_extraction: stored && !extracted,
          },
        }),
      ),
      http.post(`${API}/series/series-1/occurrences/occurrence-1/knowledge`, async ({ request }) => {
        expect(await request.json()).toEqual({ source: 'upload', text: '議事録の内容' })
        calls.push('add')
        stored = true
        return HttpResponse.json(
          { knowledge, normalization_warning: '一部の表記を確認してください', replacement_count: 2 },
          { status: 201 },
        )
      }),
      http.post(`${API}/series/series-1/occurrences/occurrence-1/extract`, () => {
        expect(stored).toBe(true)
        calls.push('extract')
        attempts += 1
        if (attempts === 1) return HttpResponse.json({ detail: 'Unavailable' }, { status: 503 })
        extracted = true
        return HttpResponse.json({ created: 1, closed: 0, truncated: true, items: [actionItem] })
      }),
    )
    renderPage(
      <Routes>
        <Route path="/series/:seriesId/occurrences/:occurrenceId" element={<OccurrencePage />} />
      </Routes>,
      '/series/series-1/occurrences/occurrence-1',
    )
    const user = userEvent.setup()
    await user.click(await screen.findByRole('button', { name: 'テキストを追加' }))
    await user.type(screen.getByLabelText('議事録・ナレッジのテキスト'), '議事録の内容')
    await user.click(screen.getByRole('button', { name: '追加して抽出' }))
    expect(await screen.findByText(/メモリの抽出に失敗しました/)).toBeInTheDocument()
    expect(screen.getByText(/2箇所を正規化しました/)).toBeInTheDocument()
    expect(screen.getByText('一部の表記を確認してください')).toBeInTheDocument()
    expect(calls).toEqual(['add', 'extract'])
    await user.click(screen.getByRole('button', { name: 'メモリ抽出を再実行' }))
    expect(await screen.findByText('抽出完了: 1件追加、0件解決')).toBeInTheDocument()
    expect(screen.getByText(/一部を切り詰めて抽出しました/)).toBeInTheDocument()
    expect(calls).toEqual(['add', 'extract', 'extract'])
  })
  it('saves documents for future occurrences without extracting or showing an error', async () => {
    let stored = false
    let extractions = 0
    const knowledge = {
      id: 'knowledge-1',
      source: 'upload',
      title: null,
      excerpt: '事前資料',
      created_at: '2026-11-13T10:00:00Z',
    }
    server.use(
      http.get(`${API}/series/series-1`, () => HttpResponse.json({ ...series, role: 'creator' })),
      http.get(`${API}/series/series-1/occurrences/occurrence-1`, () =>
        HttpResponse.json({
          ...occurrence,
          knowledge: stored ? [knowledge] : [],
          occurrence: { ...occurrence.occurrence, knowledge_count: stored ? 1 : 0, needs_extraction: stored },
        }),
      ),
      http.post(`${API}/series/series-1/occurrences/occurrence-1/knowledge`, () => {
        stored = true
        return HttpResponse.json({ knowledge, normalization_warning: null, replacement_count: 0 }, { status: 201 })
      }),
      http.post(`${API}/series/series-1/occurrences/occurrence-1/extract`, () => {
        extractions += 1
        return HttpResponse.json({ detail: 'Future occurrence' }, { status: 422 })
      }),
    )
    const { client } = renderPage(
      <Routes>
        <Route path="/series/:seriesId/occurrences/:occurrenceId" element={<OccurrencePage />} />
      </Routes>,
      '/series/series-1/occurrences/occurrence-1',
    )
    const user = userEvent.setup()
    await user.click(await screen.findByRole('button', { name: 'テキストを追加' }))
    await user.type(screen.getByLabelText('議事録・ナレッジのテキスト'), '事前資料')
    await user.click(screen.getByRole('button', { name: '追加', exact: true }))
    expect(await screen.findByText(/議事録を追加しました/)).toBeInTheDocument()
    expect(screen.getByText('会議の開始後に抽出できます')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /メモリ.*抽出/ })).not.toBeInTheDocument()
    expect(screen.queryByText('未抽出')).not.toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(client.getMutationCache().getAll()).toHaveLength(1)
    expect(extractions).toBe(0)
  })
})
