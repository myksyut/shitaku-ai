import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse, http } from 'msw'
import { describe, expect, it } from 'vitest'
import { API, renderPage, server } from '../../test/series'
import { DictionarySection } from './DictionarySection'
import type { DictionaryEntry } from './types'

const entry: DictionaryEntry = {
  id: 'entry-1',
  canonical_name: 'Shitaku',
  category: null,
  aliases: ['したく'],
  description: '会議準備',
}

describe('series dictionary', () => {
  it('lets members read terms without creator controls', async () => {
    server.use(http.get(`${API}/series/series-1/dictionary`, () => HttpResponse.json([entry])))
    renderPage(<DictionarySection seriesId="series-1" seriesRole="member" />)
    expect(await screen.findByText('Shitaku')).toBeInTheDocument()
    expect(screen.getByText('表記揺れ: したく')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '辞書を追加' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '編集' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '削除' })).not.toBeInTheDocument()
  })

  it('edits series terms without replacing a null category or existing aliases', async () => {
    let saved = entry
    server.use(
      http.get(`${API}/series/series-1/dictionary`, () => HttpResponse.json([saved])),
      http.put(`${API}/series/series-1/dictionary/entry-1`, async ({ request }) => {
        expect(await request.json()).toEqual({
          canonical_name: 'Shitaku',
          category: null,
          aliases: ['したく'],
          description: '共有の会議準備',
        })
        saved = { ...entry, description: '共有の会議準備' }
        return HttpResponse.json(saved)
      }),
    )
    renderPage(<DictionarySection seriesId="series-1" seriesRole="creator" />)
    const user = userEvent.setup()
    await user.click(await screen.findByRole('button', { name: '編集', exact: true }))
    await user.clear(screen.getByLabelText('説明'))
    await user.type(screen.getByLabelText('説明'), '共有の会議準備')
    await user.click(screen.getByRole('button', { name: '更新' }))
    expect(await screen.findByText('共有の会議準備')).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})
