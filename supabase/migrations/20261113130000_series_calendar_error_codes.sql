update public.series
set calendar_sync_error = case calendar_sync_error
    when 'Google integration not connected' then 'not_connected'
    when 'Google scope missing' then 'scope_missing'
    when 'Creator calendar event unavailable' then 'event_not_found'
    else 'calendar_unavailable'
end
where calendar_sync_error not in (
    'not_connected', 'scope_missing', 'revoked', 'attendees_omitted', 'event_not_found', 'calendar_unavailable'
);

alter table public.series add constraint series_calendar_sync_error_code check (
    calendar_sync_error in (
        'not_connected', 'scope_missing', 'revoked', 'attendees_omitted', 'event_not_found', 'calendar_unavailable'
    )
);
