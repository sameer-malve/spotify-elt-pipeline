{{ config(materialized='table') }}

SELECT
    primary_artist_id                  AS artist_id,
    primary_artist_name                AS artist_name,
    COUNT(*)                           AS track_count,
    AVG(duration_minutes)              AS avg_duration_minutes,
    SUM(CAST(is_explicit AS INT))      AS total_explicit_tracks
FROM {{ ref('stg_tracks') }}
WHERE primary_artist_id IS NOT NULL
GROUP BY primary_artist_id, primary_artist_name
