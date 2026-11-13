create schema legacy;
revoke all on schema legacy from public, anon, authenticated;
alter table public.agents set schema legacy;
alter table public.recurring_meetings set schema legacy;
alter table public.meeting_transcripts set schema legacy;
alter table public.knowledge set schema legacy;
alter table public.agendas set schema legacy;
alter table public.dictionary_entries set schema legacy;
drop table public.generated_agendas;
drop table public.slack_messages;

alter table public.google_integrations add unique (id, user_id);
alter table public.slack_integrations add unique (id, user_id);

create table public.series (
    id uuid primary key default gen_random_uuid(),
    ical_uid text not null unique,
    created_by uuid not null references auth.users(id) on delete restrict,
    creator_event_id text not null,
    google_integration_id uuid,
    title text not null,
    rrule text,
    description text check (char_length(description) <= 500),
    minutes_count smallint not null default 3 check (minutes_count between 0 and 10),
    slack_message_days smallint not null default 7 check (slack_message_days between 1 and 30),
    slack_integration_id uuid,
    slack_channels jsonb not null default '[]' check (jsonb_typeof(slack_channels) = 'array'),
    calendar_synced_at timestamptz not null default now(),
    calendar_sync_error text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    foreign key (google_integration_id, created_by) references public.google_integrations(id, user_id)
        on delete set null (google_integration_id),
    foreign key (slack_integration_id, created_by) references public.slack_integrations(id, user_id)
        on delete set null (slack_integration_id)
);
create index series_creator_idx on public.series(created_by);

create table public.series_attendees (
    series_id uuid not null references public.series(id) on delete cascade,
    email text not null check (email = lower(email) and position('@' in email) > 1),
    display_name text,
    is_organizer boolean not null default false,
    primary key (series_id, email)
);
create index series_attendees_email_idx on public.series_attendees(email);

create table public.occurrences (
    id uuid primary key default gen_random_uuid(),
    series_id uuid not null references public.series(id) on delete cascade,
    original_start timestamptz not null,
    start_at timestamptz not null,
    is_cancelled boolean not null default false,
    extracted_at timestamptz,
    unique (series_id, original_start),
    unique (id, series_id)
);
create index occurrences_series_start_idx on public.occurrences(series_id, start_at);

create table public.agenda_topics (
    id uuid primary key default gen_random_uuid(),
    series_id uuid not null,
    occurrence_id uuid not null,
    submitted_by uuid not null references auth.users(id) on delete cascade,
    author_label text not null default coalesce(auth.jwt()->'user_metadata'->>'full_name', auth.jwt()->>'email', ''),
    title text not null check (char_length(title) between 1 and 200),
    details text check (char_length(details) <= 2000),
    created_at timestamptz not null default now(),
    foreign key (occurrence_id, series_id) references public.occurrences(id, series_id) on delete cascade
);
create index agenda_topics_occurrence_idx on public.agenda_topics(occurrence_id);

create table public.memory_items (
    id uuid primary key default gen_random_uuid(),
    series_id uuid not null,
    kind text not null check (kind in ('decision', 'action_item', 'open_issue')),
    body text not null check (char_length(body) between 1 and 1000),
    origin_occurrence_id uuid not null,
    extracted boolean not null,
    extraction_key text,
    human_updated_at timestamptz,
    assignee_email text check (assignee_email = lower(assignee_email)),
    due_on date,
    resolution text,
    closed_at timestamptz,
    created_at timestamptz not null default now(),
    foreign key (origin_occurrence_id, series_id) references public.occurrences(id, series_id) on delete cascade,
    unique (origin_occurrence_id, extraction_key),
    constraint memory_closed_iff_resolved check ((resolution is null) = (closed_at is null)),
    constraint memory_assignment_actions_only check (kind = 'action_item' or (assignee_email is null and due_on is null)),
    constraint memory_resolution_fits_kind check (
        resolution is null or (kind = 'decision' and resolution = 'reversed')
        or (kind = 'action_item' and resolution in ('done', 'dropped'))
        or (kind = 'open_issue' and resolution in ('resolved', 'dropped')))
);
create index memory_series_open_idx on public.memory_items(series_id) where closed_at is null;
create index memory_origin_idx on public.memory_items(origin_occurrence_id);

create table public.knowledge (
    id uuid primary key default gen_random_uuid(),
    series_id uuid not null,
    occurrence_id uuid not null,
    source text not null check (source in ('upload', 'meet_transcript')),
    google_doc_id text,
    title text,
    original_text text not null,
    normalized_text text not null,
    created_at timestamptz not null default now(),
    foreign key (occurrence_id, series_id) references public.occurrences(id, series_id) on delete cascade,
    check ((source = 'meet_transcript') = (google_doc_id is not null)),
    unique (series_id, google_doc_id)
);
create index knowledge_occurrence_idx on public.knowledge(occurrence_id);

create table public.agendas (
    occurrence_id uuid primary key,
    series_id uuid not null,
    content text not null,
    generated_at timestamptz not null,
    updated_at timestamptz not null default now(),
    foreign key (occurrence_id, series_id) references public.occurrences(id, series_id) on delete cascade
);
create index agendas_series_idx on public.agendas(series_id);

create table public.dictionary_entries (
    id uuid primary key default gen_random_uuid(),
    series_id uuid not null references public.series(id) on delete cascade,
    canonical_name varchar(100) not null check (char_length(canonical_name) > 0),
    category text check (category in ('person', 'project', 'term', 'customer', 'abbreviation')),
    aliases text[] not null default '{}',
    description varchar(500),
    created_at timestamptz not null default now(),
    updated_at timestamptz,
    unique (series_id, canonical_name)
);

create function public.my_series_roles() returns table (series_id uuid, role text)
language sql stable security definer set search_path = '' as $$
    select s.id, 'creator'::text from public.series s where s.created_by = (select auth.uid())
    union
    select a.series_id, 'member'::text
    from public.series_attendees a
    join public.series s on s.id = a.series_id
    join auth.identities i on i.email = a.email
    where i.user_id = (select auth.uid()) and i.provider = 'google'
        and i.identity_data->'email_verified' = 'true'::jsonb and s.created_by <> (select auth.uid())
$$;

alter table public.series enable row level security;
alter table public.series_attendees enable row level security;
alter table public.occurrences enable row level security;
alter table public.agenda_topics enable row level security;
alter table public.memory_items enable row level security;
alter table public.knowledge enable row level security;
alter table public.agendas enable row level security;
alter table public.dictionary_entries enable row level security;

create policy series_read on public.series for select to authenticated
    using (id in (select r.series_id from public.my_series_roles() r));
create policy series_update on public.series for update to authenticated
    using (id in (select r.series_id from public.my_series_roles() r where r.role = 'creator'))
    with check (created_by = (select auth.uid()));
create policy series_delete on public.series for delete to authenticated
    using (id in (select r.series_id from public.my_series_roles() r where r.role = 'creator'));

do $$ declare t text; begin
    foreach t in array array['series_attendees','occurrences','agenda_topics','memory_items','knowledge','agendas','dictionary_entries'] loop
        execute format('create policy read_members on public.%I for select to authenticated using (series_id in (select r.series_id from public.my_series_roles() r))', t);
    end loop;
    foreach t in array array['memory_items','knowledge','agendas','dictionary_entries'] loop
        execute format('create policy insert_creator on public.%I for insert to authenticated with check (series_id in (select r.series_id from public.my_series_roles() r where r.role = ''creator''))', t);
        execute format('create policy delete_creator on public.%I for delete to authenticated using (series_id in (select r.series_id from public.my_series_roles() r where r.role = ''creator''))', t);
    end loop;
    foreach t in array array['memory_items','agendas','dictionary_entries'] loop
        execute format('create policy update_creator on public.%I for update to authenticated using (series_id in (select r.series_id from public.my_series_roles() r where r.role = ''creator'')) with check (series_id in (select r.series_id from public.my_series_roles() r where r.role = ''creator''))', t);
    end loop;
end $$;
create policy topics_insert on public.agenda_topics for insert to authenticated with check (
    submitted_by = (select auth.uid())
    and series_id in (select r.series_id from public.my_series_roles() r)
    and exists (select 1 from public.occurrences o where o.id = occurrence_id and o.series_id = agenda_topics.series_id
                and o.start_at > now() and not o.is_cancelled)
);
create policy topics_delete on public.agenda_topics for delete to authenticated using (
    series_id in (select r.series_id from public.my_series_roles() r)
    and (submitted_by = (select auth.uid())
         or series_id in (select r.series_id from public.my_series_roles() r where r.role = 'creator'))
);

create view public.occurrence_overview with (security_invoker = true) as
select o.*,
    (select count(*) from public.knowledge k where k.occurrence_id = o.id and k.series_id = o.series_id) knowledge_count,
    (select max(created_at) from public.knowledge k where k.occurrence_id = o.id and k.series_id = o.series_id) latest_knowledge_at,
    (select count(*) from public.agenda_topics t where t.occurrence_id = o.id and t.series_id = o.series_id) topic_count,
    exists (select 1 from public.agendas a where a.occurrence_id = o.id and a.series_id = o.series_id) has_agenda
from public.occurrences o;

create function public.apply_calendar_snapshot(p_series_id uuid, p_snapshot jsonb, p_fetched_at timestamptz)
returns void language plpgsql security invoker set search_path = '' as $$
declare v_synced timestamptz; v_omitted boolean := coalesce((p_snapshot->>'attendees_omitted')::boolean, false);
begin
    select calendar_synced_at into v_synced from public.series where id = p_series_id for update;
    if not found then raise exception 'series not found' using errcode = 'P0002'; end if;
    if p_fetched_at <= v_synced then return; end if;
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
end $$;

create function public.claim_series(p_creator_id uuid, p_integration_id uuid, p_snapshot jsonb, p_fetched_at timestamptz)
returns table (series_id uuid, created boolean) language plpgsql security invoker set search_path = '' as $$
declare v_id uuid;
begin
    insert into public.series(ical_uid, created_by, creator_event_id, google_integration_id, title, calendar_synced_at)
    values (p_snapshot->>'ical_uid', p_creator_id, p_snapshot->>'event_id', p_integration_id,
            p_snapshot->>'title', '-infinity')
    on conflict (ical_uid) do nothing returning id into v_id;
    if v_id is not null then
        perform public.apply_calendar_snapshot(v_id, p_snapshot, p_fetched_at);
        return query select v_id, true;
    else
        return query select s.id, false from public.series s where s.ical_uid = p_snapshot->>'ical_uid';
    end if;
end $$;

create function public.set_memory_item_resolution(p_item_id uuid, p_resolution text)
returns public.memory_items language plpgsql security definer set search_path = '' as $$
declare v_item public.memory_items%rowtype; v_role text;
begin
    select * into v_item from public.memory_items where id = p_item_id for update;
    if not found then raise exception 'memory item not found' using errcode = 'P0002'; end if;
    select r.role into v_role from public.my_series_roles() r where r.series_id = v_item.series_id;
    if v_role is null then raise exception 'memory item not found' using errcode = 'P0002'; end if;
    if v_item.kind <> 'action_item' and v_role <> 'creator' then
        raise exception 'only the creator can change this item' using errcode = '42501';
    end if;
    update public.memory_items set resolution = p_resolution,
        closed_at = case when p_resolution is null then null
            when v_item.resolution is not distinct from p_resolution then v_item.closed_at else now() end,
        human_updated_at = now()
    where id = p_item_id and series_id = v_item.series_id returning * into v_item;
    return v_item;
end $$;

create function public.apply_extraction(p_occurrence_id uuid, p_items jsonb, p_closures jsonb, p_input_at timestamptz)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare v_occ public.occurrences%rowtype; v_created integer; v_closed integer;
begin
    select o.* into v_occ from public.occurrences o
    where o.id = p_occurrence_id and o.series_id in
        (select r.series_id from public.my_series_roles() r where r.role = 'creator') for update;
    if not found then raise exception 'occurrence not found' using errcode = 'P0002'; end if;
    delete from public.memory_items m where m.series_id = v_occ.series_id and m.origin_occurrence_id = p_occurrence_id
        and m.extracted and m.human_updated_at is null and m.closed_at is null
        and not exists (select 1 from jsonb_array_elements(p_items) i where i->>'extraction_key' = m.extraction_key);
    insert into public.memory_items(series_id, kind, body, origin_occurrence_id, extracted, extraction_key, assignee_email, due_on)
    select v_occ.series_id, i->>'kind', i->>'body', p_occurrence_id, true, i->>'extraction_key',
        nullif(lower(i->>'assignee_email'), ''), (i->>'due_on')::date from jsonb_array_elements(p_items) i
    on conflict (origin_occurrence_id, extraction_key) do nothing;
    get diagnostics v_created = row_count;
    update public.memory_items m set resolution = c->>'resolution', closed_at = v_occ.start_at
        from jsonb_array_elements(p_closures) c where m.id = (c->>'item_id')::uuid and m.series_id = v_occ.series_id
            and m.closed_at is null and m.human_updated_at is null;
    get diagnostics v_closed = row_count;
    update public.occurrences set extracted_at = p_input_at where id = p_occurrence_id and series_id = v_occ.series_id;
    return jsonb_build_object('created', v_created, 'closed', v_closed);
end $$;

revoke all on public.series, public.series_attendees, public.occurrences, public.agenda_topics, public.memory_items,
    public.knowledge, public.agendas, public.dictionary_entries, public.occurrence_overview from public, anon, authenticated;
grant all on public.series, public.series_attendees, public.occurrences, public.agenda_topics, public.memory_items,
    public.knowledge, public.agendas, public.dictionary_entries, public.occurrence_overview to service_role;
grant select on public.series, public.series_attendees, public.occurrences, public.agenda_topics, public.memory_items,
    public.knowledge, public.agendas, public.dictionary_entries, public.occurrence_overview to authenticated;
grant update (description, minutes_count, slack_message_days, slack_integration_id, slack_channels, updated_at)
    on public.series to authenticated;
grant delete on public.series to authenticated;
grant insert, delete on public.agenda_topics, public.knowledge to authenticated;
grant insert, update, delete on public.memory_items, public.agendas, public.dictionary_entries to authenticated;
revoke all on function public.my_series_roles(), public.apply_calendar_snapshot(uuid, jsonb, timestamptz),
    public.claim_series(uuid, uuid, jsonb, timestamptz), public.set_memory_item_resolution(uuid, text),
    public.apply_extraction(uuid, jsonb, jsonb, timestamptz) from public, anon, authenticated;
grant execute on function public.apply_calendar_snapshot(uuid, jsonb, timestamptz),
    public.claim_series(uuid, uuid, jsonb, timestamptz) to service_role;
grant execute on function public.my_series_roles(), public.set_memory_item_resolution(uuid, text),
    public.apply_extraction(uuid, jsonb, jsonb, timestamptz) to authenticated, service_role;
notify pgrst, 'reload schema';
