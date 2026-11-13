drop function public.set_memory_item_resolution(uuid, text);
drop function public.apply_extraction(uuid, jsonb, jsonb, timestamptz);

create function public.set_memory_item_resolution(p_series_id uuid, p_item_id uuid, p_resolution text)
returns public.memory_items language plpgsql security definer set search_path = '' as $$
declare v_item public.memory_items%rowtype; v_role text;
begin
    select * into v_item from public.memory_items where series_id = p_series_id and id = p_item_id for update;
    if not found then raise exception 'memory item not found' using errcode = 'P0002'; end if;
    select r.role into v_role from public.my_series_roles() r where r.series_id = p_series_id;
    if v_role is null then raise exception 'memory item not found' using errcode = 'P0002'; end if;
    if v_item.kind <> 'action_item' and v_role <> 'creator' then
        raise exception 'only the creator can change this item' using errcode = '42501';
    end if;
    update public.memory_items set resolution = p_resolution,
        closed_at = case when p_resolution is null then null
            when v_item.resolution is not distinct from p_resolution then v_item.closed_at else now() end,
        human_updated_at = now()
    where id = p_item_id and series_id = p_series_id returning * into v_item;
    return v_item;
end $$;

create function public.apply_extraction(
    p_series_id uuid, p_occurrence_id uuid, p_items jsonb, p_closures jsonb, p_input_at timestamptz
) returns jsonb language plpgsql security definer set search_path = '' as $$
declare v_occ public.occurrences%rowtype; v_created integer; v_closed integer;
begin
    select o.* into v_occ from public.occurrences o
    where o.id = p_occurrence_id and o.series_id = p_series_id and o.series_id in
        (select r.series_id from public.my_series_roles() r where r.role = 'creator') for update;
    if not found then raise exception 'occurrence not found' using errcode = 'P0002'; end if;
    if p_input_at < v_occ.extracted_at then
        return jsonb_build_object('created', 0, 'closed', 0, 'stale', true);
    end if;
    update public.memory_items m set resolution = c->>'resolution', closed_at = v_occ.start_at
        from jsonb_array_elements(p_closures) c where m.id = (c->>'item_id')::uuid and m.series_id = p_series_id
            and m.closed_at is null and m.human_updated_at is null;
    get diagnostics v_closed = row_count;
    with applied as (
        insert into public.memory_items as existing
            (series_id, kind, body, origin_occurrence_id, extracted, extraction_key, assignee_email, due_on)
        select p_series_id, i->>'kind', i->>'body', p_occurrence_id, true, i->>'extraction_key',
            nullif(lower(i->>'assignee_email'), ''), (i->>'due_on')::date from jsonb_array_elements(p_items) i
        on conflict (origin_occurrence_id, extraction_key) do update
            set assignee_email = excluded.assignee_email, due_on = excluded.due_on
            where existing.series_id = p_series_id and existing.extracted
                and existing.human_updated_at is null and existing.closed_at is null
                and (existing.assignee_email, existing.due_on) is distinct from (excluded.assignee_email, excluded.due_on)
        returning existing.extraction_key
    )
    select count(*)::integer into v_created from applied a
    where not exists (
        select 1 from public.memory_items m where m.series_id = p_series_id
            and m.origin_occurrence_id = p_occurrence_id and m.extraction_key = a.extraction_key
    );
    update public.occurrences set extracted_at = p_input_at where id = p_occurrence_id and series_id = p_series_id;
    return jsonb_build_object('created', v_created, 'closed', v_closed);
end $$;
revoke all on function public.set_memory_item_resolution(uuid, uuid, text),
    public.apply_extraction(uuid, uuid, jsonb, jsonb, timestamptz) from public, anon, authenticated;
grant execute on function public.set_memory_item_resolution(uuid, uuid, text),
    public.apply_extraction(uuid, uuid, jsonb, jsonb, timestamptz) to authenticated, service_role;
notify pgrst, 'reload schema';
