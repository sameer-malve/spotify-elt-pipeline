{{ config(materialized='table') }}

WITH track_artists AS (
    SELECT
        t.track_id,
        t.popularity,
        a.value:id::VARCHAR AS artist_id
    FROM {{ ref('stg_tracks') }} t,
         LATERAL FLATTEN(input => t.raw_json:artists) a
)

SELECT
    sa.artist_id,
    sa.artist_name,
    COUNT(*)              AS track_count,
    AVG(ta.popularity)    AS avg_popularity,
    MAX(ta.popularity)    AS max_popularity
FROM track_artists ta
JOIN {{ ref('stg_artists') }} sa
    ON ta.artist_id = sa.artist_id
GROUP BY sa.artist_id, sa.artist_name
