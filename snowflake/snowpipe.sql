-- =====================================================================
-- Spotify ELT Pipeline — Snowpipe Definitions
--
-- One auto-ingest pipe per entity, each watching a sub-prefix of the
-- raw S3 zone created by `setup.sql`.
--
-- How the parse works:
--   Each S3 object is a single JSON document of the form
--     {"metadata": {...}, "data": [{...}, {...}, ...]}
--   We use LATERAL FLATTEN on `$1:data` so the COPY produces one row
--   per element of the array. `f.value` is the per-record JSON, which
--   we (a) project scalar columns from and (b) store wholesale in
--   `raw_json` for downstream replay.
--
-- After running this script:
--   1. SHOW PIPES IN SCHEMA SPOTIFY_DB.RAW;
--   2. Copy each pipe's NOTIFICATION_CHANNEL (SQS ARN) into the S3
--      bucket's event-notification config (s3:ObjectCreated:* on the
--      matching prefix) so uploads actually trigger ingest.
-- =====================================================================

USE ROLE ACCOUNTADMIN;
USE WAREHOUSE SPOTIFY_WH;
USE DATABASE  SPOTIFY_DB;
USE SCHEMA    RAW;

-- ---------------------------------------------------------------------
-- PIPE_TRACKS
--   Source : s3://spotify-elt-sameer/raw/tracks/year=.../month=.../day=.../*.json
--   Target : RAW.TRACKS — one row per Spotify track
-- ---------------------------------------------------------------------
CREATE OR REPLACE PIPE SPOTIFY_DB.RAW.PIPE_TRACKS
    AUTO_INGEST = TRUE
AS
COPY INTO SPOTIFY_DB.RAW.TRACKS (
    track_id, track_name, duration_ms, explicit, popularity,
    album_id, album_name, raw_json
)
FROM (
    SELECT
        f.value:id::VARCHAR          AS track_id,
        f.value:name::VARCHAR        AS track_name,
        f.value:duration_ms::INT     AS duration_ms,
        f.value:explicit::BOOLEAN    AS explicit,
        f.value:popularity::INT      AS popularity,
        f.value:album:id::VARCHAR    AS album_id,
        f.value:album:name::VARCHAR  AS album_name,
        f.value                      AS raw_json
    FROM @SPOTIFY_DB.RAW.SPOTIFY_S3_STAGE/tracks/ s,
         LATERAL FLATTEN(input => s.$1:data) f
);

-- ---------------------------------------------------------------------
-- PIPE_AUDIO_FEATURES
--   Source : s3://spotify-elt-sameer/raw/audio_features/...
--   Target : RAW.AUDIO_FEATURES — derived features per track
-- ---------------------------------------------------------------------
CREATE OR REPLACE PIPE SPOTIFY_DB.RAW.PIPE_AUDIO_FEATURES
    AUTO_INGEST = TRUE
AS
COPY INTO SPOTIFY_DB.RAW.AUDIO_FEATURES (
    track_id, duration_ms, explicit, popularity, raw_json
)
FROM (
    SELECT
        f.value:id::VARCHAR        AS track_id,
        f.value:duration_ms::INT   AS duration_ms,
        f.value:explicit::BOOLEAN  AS explicit,
        f.value:popularity::INT    AS popularity,
        f.value                    AS raw_json
    FROM @SPOTIFY_DB.RAW.SPOTIFY_S3_STAGE/audio_features/ s,
         LATERAL FLATTEN(input => s.$1:data) f
);

-- ---------------------------------------------------------------------
-- PIPE_ARTISTS
--   Source : s3://spotify-elt-sameer/raw/artists/...
--   Target : RAW.ARTISTS — deduplicated artists across the day's tracks
-- ---------------------------------------------------------------------
CREATE OR REPLACE PIPE SPOTIFY_DB.RAW.PIPE_ARTISTS
    AUTO_INGEST = TRUE
AS
COPY INTO SPOTIFY_DB.RAW.ARTISTS (
    artist_id, artist_name, raw_json
)
FROM (
    SELECT
        f.value:id::VARCHAR    AS artist_id,
        f.value:name::VARCHAR  AS artist_name,
        f.value                AS raw_json
    FROM @SPOTIFY_DB.RAW.SPOTIFY_S3_STAGE/artists/ s,
         LATERAL FLATTEN(input => s.$1:data) f
);

-- ---------------------------------------------------------------------
-- Post-deploy sanity check: list pipes and their SQS notification
-- channels (paste the SQS ARN into S3 event notifications).
-- ---------------------------------------------------------------------
SHOW PIPES IN SCHEMA SPOTIFY_DB.RAW;
