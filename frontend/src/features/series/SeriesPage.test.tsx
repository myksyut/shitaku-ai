import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse, http } from 'msw'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { API, renderPage, series, server } from '../../test/series'
import { SeriesPage } from './SeriesPage'
import type { SeriesRole } from './types'

function open(role: SeriesRole) {
  server.use(http.get(`${API}/series/series-1`, () => HttpResponse.json({ ...series, role })))
  return renderPage(
    <Routes>
      <Route path="/series/:seriesId" element={<SeriesPage />} />
    </Routes>,
    '/series/series-1',
  )
}

describe('series permissions', () => {
  it.each(['member', 'creator'] as const)('%s sees only the controls their role allows', async (role) => {
    open(role)
    expect(await screen.findByRole('heading', { name: '開発定例' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '設定', exact: true }) !== null).toBe(role === 'creator')
    await userEvent.click(screen.getByRole('button', { name: 'チームメモリ' }))
    expect(await screen.findByRole('checkbox', { name: '見積もりを共有するを完了' })).toBeInTheDocument()
    expect(screen.getByText('2回持ち越し')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'メモリを追加' }) !== null).toBe(role === 'creator')
    expect(screen.queryByRole('button', { name: '編集', exact: true }) !== null).toBe(role === 'creator')
    expect(screen.queryByRole('button', { name: '削除', exact: true }) !== null).toBe(role === 'creator')
    await userEvent.click(screen.getByRole('button', { name: '辞書', exact: true }))
    await screen.findByText('辞書エントリがありません')
    expect(screen.queryByRole('button', { name: '辞書を追加' }) !== null).toBe(role === 'creator')
  })
})
