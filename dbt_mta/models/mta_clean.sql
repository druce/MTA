with mta_clean as (
    select
        date_time,
        date,
        mta_diff.station,
        mta_diff.turnstile,
        entries,
        exits,
        entry_avg.entries_cutoff,
        exit_avg.exits_cutoff
    from
        {{ref('mta_diff')}} mta_diff
        left outer join {{ref('entry_avg')}} entry_avg on mta_diff.station=entry_avg.station and mta_diff.turnstile=entry_avg.turnstile
        left outer join {{ref('exit_avg')}} exit_avg on mta_diff.station=exit_avg.station and mta_diff.turnstile=exit_avg.turnstile
    )
select * from mta_clean

{{ config(
  post_hook = "
    update mta_clean set entries_cutoff = 2000 where entries_cutoff is null;
    update mta_clean set exits_cutoff = 2000 where exits_cutoff is null;
    delete from mta_clean where entries > entries_cutoff;
    delete from mta_clean where exits > exits_cutoff;
") }}

{# should probably not do post_hook update, add another model with a filter and a formula #}
