import { fireEvent, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse, http } from 'msw'
import { describe, expect, it } from 'vitest'
import { API, renderPage, series, server } from '../../test/series'
import { SeriesSettingsPanel } from './SeriesSettingsPanel'

const minutesError = '参照する議事録の件数は0〜10の整数で入力してください'
const daysError = 'Slackの参照日数は1〜30の整数で入力してください'

describe('series settings bounds', () => {
  it.each([
    ['参照する議事録の件数', '-1', minutesError],
    ['参照する議事録の件数', '11', minutesError],
    ['参照する議事録の件数', '1.5', minutesError],
    ['参照する議事録の件数', '', minutesError],
    ['Slackの参照日数', '0', daysError],
    ['Slackの参照日数', '31', daysError],
    ['Slackの参照日数', '1.5', daysError],
    ['Slackの参照日数', '', daysError],
  ])('rejects %s = %s with an inline error', async (label, value, error) => {
    const { client } = renderPage(<SeriesSettingsPanel series={{ ...series, role: 'creator' }} />)
    const user = userEvent.setup()
    const input = screen.getByRole<HTMLInputElement>('spinbutton', { name: label })
    await user.clear(input)
    if (value) await user.type(input, value)
    expect(input).toHaveAttribute('aria-invalid', 'true')
    expect(input.checkValidity()).toBe(false)
    expect(screen.getByText(error)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '設定を保存' })).toBeDisabled()
    if (!input.form) throw new Error('Settings input must belong to the settings form')
    fireEvent.submit(input.form)
    expect(client.getMutationCache().getAll()).toHaveLength(0)
  })

  it.each([
    [0, 1],
    [10, 30],
  ])('accepts boundary values %i minutes and %i days', async (minutes, days) => {
    server.use(
      http.put(`${API}/series/series-1/settings`, async ({ request }) => {
        expect(await request.json()).toEqual({
          description: null,
          minutes_count: minutes,
          slack_message_days: days,
          slack: null,
        })
        return HttpResponse.json({
          ...series,
          settings: { description: null, minutes_count: minutes, slack_message_days: days },
        })
      }),
    )
    renderPage(<SeriesSettingsPanel series={{ ...series, role: 'creator' }} />)
    const user = userEvent.setup()
    const minutesInput = screen.getByRole('spinbutton', { name: '参照する議事録の件数' })
    const daysInput = screen.getByRole('spinbutton', { name: 'Slackの参照日数' })
    expect(minutesInput).toHaveAttribute('min', '0')
    expect(minutesInput).toHaveAttribute('max', '10')
    expect(daysInput).toHaveAttribute('min', '1')
    expect(daysInput).toHaveAttribute('max', '30')
    await user.clear(minutesInput)
    await user.type(minutesInput, String(minutes))
    await user.clear(daysInput)
    await user.type(daysInput, String(days))
    expect(screen.queryByText(minutesError)).not.toBeInTheDocument()
    expect(screen.queryByText(daysError)).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '設定を保存' }))
    expect(await screen.findByText('設定を保存しました')).toBeInTheDocument()
  })
})
