update public.series set slack_channels = '[]'::jsonb
where slack_integration_id is null and slack_channels <> '[]'::jsonb;

create function public.clear_disconnected_slack_channels()
returns trigger language plpgsql set search_path = '' as $$
begin
    if new.slack_integration_id is null then new.slack_channels := '[]'::jsonb; end if;
    return new;
end $$;
revoke all on function public.clear_disconnected_slack_channels() from public, anon, authenticated;
create trigger series_clear_disconnected_slack before update of slack_integration_id on public.series
    for each row execute function public.clear_disconnected_slack_channels();

alter table public.series add constraint series_slack_channels_require_integration
    check (slack_integration_id is not null or slack_channels = '[]'::jsonb);
