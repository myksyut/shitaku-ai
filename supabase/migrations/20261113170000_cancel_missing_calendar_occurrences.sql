create or replace function public.apply_calendar_snapshot(p_series_id uuid, p_snapshot jsonb, p_fetched_at timestamptz)
returns void language plpgsql security invoker set search_path = '' as $$
declare
    v_synced timestamptz;
    v_omitted boolean := coalesce((p_snapshot->>'attendees_omitted')::boolean, false);
    v_window_start timestamptz := (p_snapshot->>'window_start')::timestamptz;
    v_window_end timestamptz := (p_snapshot->>'window_end')::timestamptz;
begin
    select calendar_synced_at into v_synced from public.series where id = p_series_id for update;
    if not found then raise exception 'series not found' using errcode = 'P0002'; end if;
    if p_fetched_at <= v_synced then return; end if;
    if v_window_start is null or v_window_end is null or v_window_start >= v_window_end then
        raise exception 'calendar snapshot requires a valid fetched window' using errcode = '22023';
    end if;
    update public.series set title = p_snapshot->>'title', rrule = p_snapshot->>'rrule',
        calendar_synced_at = p_fetched_at, calendar_sync_error = case when v_omitted then 'attendees_omitted' end,
        updated_at = now() where id = p_series_id;
    if not v_omitted then
        insert into public.series_attendees(series_id, email, display_name, is_organizer)
        select p_series_id, lower(a->>'email'), a->>'display_name', coalesce((a->>'is_organizer')::boolean, false)
        from jsonb_array_elements(p_snapshot->'attendees') a
        on conflict (series_id, email) do update set display_name = excluded.display_name, is_organizer = excluded.is_organizer;
        delete from public.series_attendees sa where sa.series_id = p_series_id
            and not exists (select 1 from jsonb_array_elements(p_snapshot->'attendees') a where lower(a->>'email') = sa.email);
    end if;
    insert into public.occurrences(series_id, original_start, start_at, is_cancelled)
    select p_series_id, (o->>'original_start')::timestamptz, (o->>'start_at')::timestamptz,
        coalesce((o->>'is_cancelled')::boolean, false) from jsonb_array_elements(p_snapshot->'occurrences') o
    on conflict (series_id, original_start) do update set start_at = excluded.start_at, is_cancelled = excluded.is_cancelled;
    update public.occurrences o set is_cancelled = true
    where o.series_id = p_series_id and o.original_start >= v_window_start and o.original_start < v_window_end
        and not exists (select 1 from jsonb_array_elements(p_snapshot->'occurrences') item
                        where (item->>'original_start')::timestamptz = o.original_start);
end $$;

create function public.mark_calendar_event_missing(p_series_id uuid, p_fetched_at timestamptz)
returns void language plpgsql security invoker set search_path = '' as $$
declare v_synced timestamptz;
begin
    select calendar_synced_at into v_synced from public.series where id = p_series_id for update;
    if not found then raise exception 'series not found' using errcode = 'P0002'; end if;
    if p_fetched_at <= v_synced then return; end if;
    update public.occurrences set is_cancelled = true
        where series_id = p_series_id and start_at >= p_fetched_at;
    update public.series set calendar_synced_at = p_fetched_at, calendar_sync_error = 'event_not_found', updated_at = now()
        where id = p_series_id;
end $$;
revoke all on function public.mark_calendar_event_missing(uuid, timestamptz) from public, anon, authenticated;
grant execute on function public.mark_calendar_event_missing(uuid, timestamptz) to service_role;
notify pgrst, 'reload schema';
