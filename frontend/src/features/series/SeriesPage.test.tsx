import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse, http } from 'msw'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { API, renderPage, series, server } from '../../test/series'
import { SeriesPage } from './SeriesPage'
import type { SeriesRole } from './types'

function open(role: SeriesRole, calendar = series.calendar) {
  server.use(http.get(`${API}/series/series-1`, () => HttpResponse.json({ ...series, role, calendar })))
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
  it.each([
    ['member', 'カレンダー同期でエラーが発生しています（作成者に確認してください）'],
    ['creator', '作成者のGoogle連携が切れています'],
  ] as const)('shows a role-appropriate calendar banner for %s', async (role, expected) => {
    open(role, { ...series.calendar, error: 'not_connected', google_connected: false })
    expect(await screen.findByRole('alert')).toHaveTextContent(expected)
    expect(screen.queryByText('not_connected')).not.toBeInTheDocument()
    if (role === 'creator') {
      await userEvent.click(screen.getByRole('button', { name: '設定', exact: true }))
      expect(screen.getAllByRole('alert')).toHaveLength(2)
      for (const alert of screen.getAllByRole('alert')) expect(alert).toHaveTextContent(expected)
      expect(screen.getByRole('link', { name: 'Google連携を確認' })).toBeInTheDocument()
    } else {
      expect(screen.queryByText('作成者のGoogle連携が切れています')).not.toBeInTheDocument()
      expect(screen.queryByRole('link', { name: 'Google連携を確認' })).not.toBeInTheDocument()
    }
  })
})
