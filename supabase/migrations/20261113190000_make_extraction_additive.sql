create or replace function public.apply_extraction(
    p_occurrence_id uuid, p_items jsonb, p_closures jsonb, p_input_at timestamptz
) returns jsonb language plpgsql security definer set search_path = '' as $$
declare v_occ public.occurrences%rowtype; v_created integer; v_closed integer;
begin
    select o.* into v_occ from public.occurrences o
    where o.id = p_occurrence_id and o.series_id in
        (select r.series_id from public.my_series_roles() r where r.role = 'creator') for update;
    if not found then raise exception 'occurrence not found' using errcode = 'P0002'; end if;
    if p_input_at < v_occ.extracted_at then
        return jsonb_build_object('created', 0, 'closed', 0, 'stale', true);
    end if;
    update public.memory_items m set resolution = c->>'resolution', closed_at = v_occ.start_at
        from jsonb_array_elements(p_closures) c where m.id = (c->>'item_id')::uuid and m.series_id = v_occ.series_id
            and m.closed_at is null and m.human_updated_at is null;
    get diagnostics v_closed = row_count;
    with applied as (
        insert into public.memory_items as existing
            (series_id, kind, body, origin_occurrence_id, extracted, extraction_key, assignee_email, due_on)
        select v_occ.series_id, i->>'kind', i->>'body', p_occurrence_id, true, i->>'extraction_key',
            nullif(lower(i->>'assignee_email'), ''), (i->>'due_on')::date from jsonb_array_elements(p_items) i
        on conflict (origin_occurrence_id, extraction_key) do update
            set assignee_email = excluded.assignee_email, due_on = excluded.due_on
            where existing.series_id = v_occ.series_id and existing.extracted
                and existing.human_updated_at is null and existing.closed_at is null
                and (existing.assignee_email, existing.due_on) is distinct from (excluded.assignee_email, excluded.due_on)
        returning existing.extraction_key
    )
    select count(*)::integer into v_created from applied a
    where not exists (
        select 1 from public.memory_items m where m.series_id = v_occ.series_id
            and m.origin_occurrence_id = p_occurrence_id and m.extraction_key = a.extraction_key
    );
    update public.occurrences set extracted_at = p_input_at where id = p_occurrence_id and series_id = v_occ.series_id;
    return jsonb_build_object('created', v_created, 'closed', v_closed);
end $$;
