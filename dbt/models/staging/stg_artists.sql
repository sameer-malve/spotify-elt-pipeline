WITH ranked AS (
    SELECT
        artist_id,
        artist_name,
        _loaded_at,
        ROW_NUMBER() OVER (PARTITION BY artist_id ORDER BY _loaded_at DESC) AS rn
    FROM {{ source('raw', 'v_artists') }}
    WHERE artist_id IS NOT NULL
)

SELECT
    artist_id,
    artist_name,
    _loaded_at
FROM ranked
WHERE rn = 1
