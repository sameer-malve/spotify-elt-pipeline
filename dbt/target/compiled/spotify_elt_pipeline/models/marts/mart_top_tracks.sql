

SELECT
    t.track_id,
    t.track_name,
    t.duration_ms,
    t.duration_minutes,
    t.is_explicit,
    t.popularity,
    t.album_id,
    t.album_name,
    ROUND((t.popularity * 0.6 + (1 - t.is_explicit::INT) * 0.4) * 100, 2) AS mood_score,
    CASE
        WHEN t.is_explicit = TRUE  AND t.popularity > 70 THEN 'Explicit Banger'
        WHEN t.is_explicit = FALSE AND t.popularity > 70 THEN 'Family Friendly Hit'
        WHEN t.popularity < 40                            THEN 'Underground'
        ELSE 'Mid Tier'
    END AS audio_profile,
    t._loaded_at
FROM SPOTIFY_DB.STAGING.stg_tracks t
JOIN SPOTIFY_DB.STAGING.stg_audio_features af
    ON t.track_id = af.track_id