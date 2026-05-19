WITH ranked AS (
    SELECT
        track_id,
        track_name,
        duration_ms,
        ROUND(duration_ms / 60000.0, 2) AS duration_minutes,
        explicit AS is_explicit,
        album_id,
        album_name,
        primary_artist_id,
        primary_artist_name,
        _loaded_at,
        ROW_NUMBER() OVER (PARTITION BY track_id ORDER BY _loaded_at DESC) AS rn
    FROM {{ source('raw', 'v_tracks') }}
    WHERE track_id IS NOT NULL
)

SELECT
    track_id,
    track_name,
    duration_ms,
    duration_minutes,
    is_explicit,
    album_id,
    album_name,
    primary_artist_id,
    primary_artist_name,
    _loaded_at
FROM ranked
WHERE rn = 1
