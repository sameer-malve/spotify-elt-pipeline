WITH ranked AS (
    SELECT
        track_id,
        duration_ms,
        explicit AS is_explicit,
        _loaded_at,
        ROW_NUMBER() OVER (PARTITION BY track_id ORDER BY _loaded_at DESC) AS rn
    FROM {{ source('raw', 'v_audio_features') }}
    WHERE track_id IS NOT NULL
)

SELECT
    track_id,
    duration_ms,
    is_explicit,
    _loaded_at
FROM ranked
WHERE rn = 1
