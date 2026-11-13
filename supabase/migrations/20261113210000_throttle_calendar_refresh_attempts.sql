alter table public.series add column calendar_refresh_attempted_at timestamptz;
update public.series set calendar_refresh_attempted_at = calendar_synced_at;
alter table public.series alter column calendar_refresh_attempted_at set default now();

create function public.begin_calendar_refresh(p_series_id uuid, p_attempted_at timestamptz, p_throttle boolean)
returns boolean language plpgsql security invoker set search_path = '' as $$
declare v_attempted_at timestamptz;
begin
    select calendar_refresh_attempted_at into v_attempted_at from public.series where id = p_series_id for update;
    if not found then raise exception 'series not found' using errcode = 'P0002'; end if;
    if p_throttle and v_attempted_at > p_attempted_at - interval '2 minutes' then return false; end if;
    update public.series set calendar_refresh_attempted_at = greatest(calendar_refresh_attempted_at, p_attempted_at)
        where id = p_series_id;
    return true;
end $$;
revoke all on function public.begin_calendar_refresh(uuid, timestamptz, boolean) from public, anon, authenticated;
grant execute on function public.begin_calendar_refresh(uuid, timestamptz, boolean) to service_role;
notify pgrst, 'reload schema';
