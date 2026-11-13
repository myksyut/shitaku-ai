create view public.series_summary with (security_invoker = true) as
select s.id, s.title, s.created_by, s.calendar_sync_error,
    case when n.id is null then null else to_jsonb(n) end as next_occurrence,
    (select count(*) from public.memory_items m
     where m.series_id = s.id and m.kind = 'action_item' and m.closed_at is null) as open_action_items
from public.series s
left join lateral (
    select o.id, o.start_at, o.is_cancelled, o.has_agenda, o.knowledge_count, o.topic_count,
        (o.latest_knowledge_at is not null and (o.extracted_at is null or o.latest_knowledge_at > o.extracted_at))
            as needs_extraction
    from public.occurrence_overview o
    where o.series_id = s.id and not o.is_cancelled and o.start_at > now()
    order by o.start_at, o.id limit 1
) n on true
where s.id in (select r.series_id from public.my_series_roles() r);
revoke all on public.series_summary from public, anon, authenticated;
grant select on public.series_summary to authenticated, service_role;
notify pgrst, 'reload schema';
