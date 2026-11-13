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
    delete from public.memory_items m where m.series_id = v_occ.series_id and m.origin_occurrence_id = p_occurrence_id
        and m.extracted and m.human_updated_at is null and m.closed_at is null
        and not exists (select 1 from jsonb_array_elements(p_items) i where i->>'extraction_key' = m.extraction_key);
    insert into public.memory_items(series_id, kind, body, origin_occurrence_id, extracted, extraction_key, assignee_email, due_on)
    select v_occ.series_id, i->>'kind', i->>'body', p_occurrence_id, true, i->>'extraction_key',
        nullif(lower(i->>'assignee_email'), ''), (i->>'due_on')::date from jsonb_array_elements(p_items) i
    on conflict (origin_occurrence_id, extraction_key) do nothing;
    get diagnostics v_created = row_count;
    update public.occurrences set extracted_at = p_input_at where id = p_occurrence_id and series_id = v_occ.series_id;
    return jsonb_build_object('created', v_created, 'closed', v_closed);
end $$;
