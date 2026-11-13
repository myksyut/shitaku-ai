import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse, http } from 'msw'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { API, renderPage, series, server } from '../../test/series'
import { CalendarEventPicker } from './CalendarEventPicker'

function calendar() {
  server.use(
    http.get(`${API}/google/integrations`, () =>
      HttpResponse.json([
        {
          id: 'google-1',
          email: 'member@example.com',
          granted_scopes: ['https://www.googleapis.com/auth/calendar.readonly'],
          created_at: '',
          updated_at: null,
        },
      ]),
    ),
    http.get(`${API}/calendar/recurring-events`, ({ request }) => {
      expect(new URL(request.url).searchParams.get('google_integration_id')).toBe('google-1')
      return HttpResponse.json({
        events: [
          { calendar_event_id: 'event-1', title: '開発定例', rrule: 'FREQ=WEEKLY', attendee_count: 3, series_id: null },
        ],
      })
    }),
  )
}

describe('CalendarEventPicker', () => {
  it.each([
    [403, '作成者のカレンダーの参加者に含まれていません（招待直後なら数分後に再試行してください）'],
    [422, 'この予定の参加者ではありません'],
    [404, 'カレンダーに予定が見つかりません'],
  ])('explains claim status %i without exposing an unrelated error', async (status, message) => {
    calendar()
    server.use(http.post(`${API}/series`, () => HttpResponse.json({ detail: 'Backend message' }, { status })))
    renderPage(<CalendarEventPicker />)
    await userEvent.click(await screen.findByRole('button', { name: 'Shitakuで準備する' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(message)
  })

  it('claims the selected event and opens the shared series', async () => {
    calendar()
    server.use(
      http.post(`${API}/series`, async ({ request }) => {
        expect(await request.json()).toEqual({ google_integration_id: 'google-1', calendar_event_id: 'event-1' })
        return HttpResponse.json({ outcome: 'joined', series })
      }),
    )
    renderPage(
      <Routes>
        <Route path="/" element={<CalendarEventPicker />} />
        <Route path="/series/:seriesId" element={<h1>共有の定例</h1>} />
      </Routes>,
    )
    await userEvent.click(await screen.findByRole('button', { name: 'Shitakuで準備する' }))
    expect(await screen.findByRole('heading', { name: '共有の定例' })).toBeInTheDocument()
  })
  it('disables full-calendar-only integrations without requesting their events', async () => {
    let eventReads = 0
    server.use(
      http.get(`${API}/google/integrations`, () =>
        HttpResponse.json([
          {
            id: 'google-full',
            email: 'full@example.com',
            granted_scopes: ['https://www.googleapis.com/auth/calendar'],
            created_at: '',
            updated_at: null,
          },
        ]),
      ),
      http.get(`${API}/calendar/recurring-events`, () => {
        eventReads += 1
        return HttpResponse.json({ events: [] })
      }),
    )
    renderPage(<CalendarEventPicker />)
    expect(
      await screen.findByRole('option', { name: 'full@example.com（カレンダーの読み取り権限を追加してください）' }),
    ).toBeDisabled()
    expect(screen.getByLabelText('Googleアカウント')).toHaveValue('')
    expect(screen.getByRole('link', { name: 'Google連携設定' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Shitakuで準備する' })).not.toBeInTheDocument()
    expect(eventReads).toBe(0)
  })

  it('selects a readonly-capable account while leaving other integrations visible but disabled', async () => {
    calendar()
    server.use(
      http.get(`${API}/google/integrations`, () =>
        HttpResponse.json([
          {
            id: 'google-full',
            email: 'full@example.com',
            granted_scopes: ['https://www.googleapis.com/auth/calendar'],
            created_at: '',
            updated_at: null,
          },
          {
            id: 'google-1',
            email: 'member@example.com',
            granted_scopes: ['https://www.googleapis.com/auth/calendar.readonly'],
            created_at: '',
            updated_at: null,
          },
        ]),
      ),
    )
    renderPage(<CalendarEventPicker />)
    expect(await screen.findByRole('button', { name: 'Shitakuで準備する' })).toBeInTheDocument()
    expect(screen.getByLabelText('Googleアカウント')).toHaveValue('google-1')
    expect(screen.getByRole('option', { name: /full@example.com/ })).toBeDisabled()
    expect(screen.getByRole('option', { name: 'member@example.com' })).toBeEnabled()
  })
})
