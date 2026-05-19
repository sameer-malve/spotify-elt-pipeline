
  
    

create or replace transient table SPOTIFY_DB.STAGING.mart_artist_summary
    
    
    
    as (

WITH track_artists AS (
    SELECT
        t.track_id,
        t.popularity,
        a.value:id::VARCHAR AS artist_id
    FROM SPOTIFY_DB.STAGING.stg_tracks t,
         LATERAL FLATTEN(input => t.raw_json:artists) a
)

SELECT
    sa.artist_id,
    sa.artist_name,
    COUNT(*)              AS track_count,
    AVG(ta.popularity)    AS avg_popularity,
    MAX(ta.popularity)    AS max_popularity
FROM track_artists ta
JOIN SPOTIFY_DB.STAGING.stg_artists sa
    ON ta.artist_id = sa.artist_id
GROUP BY sa.artist_id, sa.artist_name
    )
;


  