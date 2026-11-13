alter table public.agenda_topics alter column author_label set default 'メンバー';

create function public.set_agenda_topic_author()
returns trigger language plpgsql security definer set search_path = '' as $$
declare v_email text; v_display_name text;
begin
    select i.email, nullif(btrim(a.display_name), '') into v_email, v_display_name
    from auth.identities i
    left join public.series_attendees a on a.series_id = new.series_id and a.email = i.email
    where i.user_id = (select auth.uid()) and i.provider = 'google'
        and i.identity_data->'email_verified' = 'true'::jsonb
    order by (a.email is null), (nullif(btrim(a.display_name), '') is null), i.email
    limit 1;
    new.author_label := coalesce(v_display_name, v_email, 'メンバー');
    return new;
end $$;
revoke all on function public.set_agenda_topic_author() from public, anon, authenticated;
create trigger agenda_topics_trusted_author before insert on public.agenda_topics
    for each row execute function public.set_agenda_topic_author();

revoke insert on public.agenda_topics from authenticated;
grant insert (series_id, occurrence_id, submitted_by, title, details) on public.agenda_topics to authenticated;
notify pgrst, 'reload schema';
