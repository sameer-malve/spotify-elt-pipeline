
  create or replace   view SPOTIFY_DB.STAGING.stg_artists
  
  
  
  
  as (
    WITH ranked AS (
    SELECT
        artist_id,
        artist_name,
        _loaded_at,
        ROW_NUMBER() OVER (PARTITION BY artist_id ORDER BY _loaded_at DESC) AS rn
    FROM SPOTIFY_DB.RAW.v_artists
    WHERE artist_id IS NOT NULL
)

SELECT
    artist_id,
    artist_name,
    _loaded_at
FROM ranked
WHERE rn = 1
  );

