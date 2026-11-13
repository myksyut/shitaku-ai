import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse, http } from 'msw'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { API, occurrence, renderPage, series, server } from '../../test/series'
import { OccurrencePage } from './OccurrencePage'
import type { OccurrenceDetail, SeriesRole } from './types'

function open(role: SeriesRole, detail: OccurrenceDetail = occurrence) {
  server.use(
    http.get(`${API}/series/series-1`, () => HttpResponse.json({ ...series, role })),
    http.get(`${API}/series/series-1/occurrences/occurrence-1`, () => HttpResponse.json(detail)),
  )
  return renderPage(
    <Routes>
      <Route path="/series/:seriesId/occurrences/:occurrenceId" element={<OccurrencePage />} />
    </Routes>,
    '/series/series-1/occurrences/occurrence-1',
  )
}

describe('occurrence permissions', () => {
  it.each(['member', 'creator'] as const)('%s gets the appropriate meeting controls', async (role) => {
    open(role)
    expect(await screen.findByRole('button', { name: '議題を投稿' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '自分の議題を取り下げ' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '他の参加者の議題を取り下げ' }) !== null).toBe(role === 'creator')
    expect(screen.queryByRole('button', { name: 'アジェンダを生成' }) !== null).toBe(role === 'creator')
    expect(screen.queryByRole('button', { name: 'テキストを追加' }) !== null).toBe(role === 'creator')
    expect(screen.queryByRole('button', { name: 'Meetから追加' }) !== null).toBe(role === 'creator')
  })

  it.each([
    { ...occurrence.occurrence, is_cancelled: true },
    { ...occurrence.occurrence, start_at: '2020-01-01T10:00:00Z' },
  ])('does not invite topic submissions to cancelled or past meetings', async (summary) => {
    open('member', { ...occurrence, occurrence: summary })
    await screen.findByRole('heading', { name: '議題の投稿' })
    expect(screen.queryByRole('button', { name: '議題を投稿' })).not.toBeInTheDocument()
  })

  it('keeps markdown and copying available to members but not agenda editing', async () => {
    const clipboard = { writeText: vi.fn().mockResolvedValue(undefined) }
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: clipboard })
    const content = '## 事前に投稿された議題\n- 共有された議題'
    open('member', {
      ...occurrence,
      agenda: { occurrence_id: 'occurrence-1', content, generated_at: '', updated_at: 'version-1' },
    })
    expect(await screen.findByRole('heading', { name: '事前に投稿された議題' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '編集', exact: true })).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'コピー', exact: true }))
    expect(clipboard.writeText).toHaveBeenCalledWith(content)
  })
})
