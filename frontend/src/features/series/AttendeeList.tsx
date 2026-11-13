import { Card } from '../../components/ui'
import { Badge } from './SeriesUi'
import type { Attendee } from './types'

export function AttendeeList({ attendees }: { attendees: Attendee[] }) {
  return (
    <Card className="space-y-3">
      <h2 className="font-bold">
        参加者 <span className="text-sm font-normal">{attendees.length}人</span>
      </h2>
      <p className="text-xs text-[var(--color-warm-gray-500)]">作成者のカレンダーの招待客から自動的に決まります。</p>
      <ul className="flex flex-wrap gap-3">
        {attendees.map((attendee) => (
          <li key={attendee.email} className="rounded-xl bg-[var(--color-cream-100)] p-3 text-sm">
            <p className="font-semibold">
              {attendee.display_name ?? attendee.email} {attendee.is_organizer && <Badge>主催者</Badge>}
            </p>
            {attendee.display_name && <p className="text-xs text-[var(--color-warm-gray-500)]">{attendee.email}</p>}
          </li>
        ))}
      </ul>
    </Card>
  )
}
