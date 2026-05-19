
    
    

select
    artist_id as unique_field,
    count(*) as n_records

from SPOTIFY_DB.STAGING.mart_artist_summary
where artist_id is not null
group by artist_id
having count(*) > 1


