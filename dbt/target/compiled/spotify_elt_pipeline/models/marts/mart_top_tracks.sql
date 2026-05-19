

SELECT
    t.track_id,
    t.track_name,
    t.duration_ms,
    t.duration_minutes,
    CAST(t.is_explicit AS BOOLEAN) AS is_explicit,
    t.album_id,
    t.album_name,
    ROUND(
        CASE WHEN t.is_explicit THEN 0.3 ELSE 0.7 END
        + (t.duration_ms / 1000000.0),
        4
    ) AS mood_score,
    CASE
        WHEN t.is_explicit = TRUE                                THEN 'Explicit Track'
        WHEN t.is_explicit = FALSE AND t.duration_minutes > 3.5  THEN 'Clean Track'
        ELSE 'Short Clean'
    END AS audio_profile,
    t._loaded_at
FROM SPOTIFY_DB.STAGING.stg_tracks t
JOIN SPOTIFY_DB.STAGING.stg_audio_features af
    ON t.track_id = af.track_id