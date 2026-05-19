-- =====================================================================
-- Spotify ELT Pipeline — Snowflake Setup
--
-- Idempotent bootstrap for the Snowflake account. Re-running this
-- script is a no-op for already-existing objects (every statement is
-- either CREATE ... IF NOT EXISTS or CREATE OR REPLACE).
--
-- Creates: database, schemas, warehouse, role, raw tables, JSON file
-- format, and the S3 external stage that Snowpipe reads from.
--
-- Run as a role with sufficient privileges to create account-level
-- objects (e.g. ACCOUNTADMIN, or SYSADMIN + USERADMIN for the role).
-- =====================================================================

USE ROLE ACCOUNTADMIN;

-- ---------------------------------------------------------------------
-- Warehouse
--   X-SMALL is plenty for the ~50-row daily extract. Aggressive
--   auto-suspend (60s) keeps credits down on bursty workloads, and
--   AUTO_RESUME means dbt / Streamlit / ad-hoc queries don't have to
--   wake it up manually.
-- ---------------------------------------------------------------------
CREATE WAREHOUSE IF NOT EXISTS SPOTIFY_WH
    WITH
        WAREHOUSE_SIZE = 'XSMALL'
        AUTO_SUSPEND = 60
        AUTO_RESUME = TRUE
        INITIALLY_SUSPENDED = TRUE
    COMMENT = 'Warehouse for the Spotify ELT pipeline (extract -> load -> transform)';

-- ---------------------------------------------------------------------
-- Database and schemas
--   RAW     — raw landed JSON from S3 via Snowpipe
--   STAGING — dbt typed/cleaned views over RAW
--   MARTS   — dbt production-facing tables for the dashboard
-- ---------------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS SPOTIFY_DB
    COMMENT = 'Spotify ELT pipeline database';

CREATE SCHEMA IF NOT EXISTS SPOTIFY_DB.RAW
    COMMENT = 'Raw landed JSON from the Spotify extractor';

CREATE SCHEMA IF NOT EXISTS SPOTIFY_DB.STAGING
    COMMENT = 'dbt staging models (typed views over RAW)';

CREATE SCHEMA IF NOT EXISTS SPOTIFY_DB.MARTS
    COMMENT = 'dbt marts (production-facing tables)';

-- ---------------------------------------------------------------------
-- Role and grants
--   SPOTIFY_ROLE is the workload role used by Airflow + dbt + Streamlit.
--   Per spec it gets USAGE on the warehouse, the database, and every
--   schema. Object-level privileges (SELECT on tables, ownership of
--   pipes, CREATE on the dbt target schemas, etc.) should be granted
--   explicitly per workload — keep the blast radius small.
-- ---------------------------------------------------------------------
CREATE ROLE IF NOT EXISTS SPOTIFY_ROLE
    COMMENT = 'Workload role for the Spotify ELT pipeline';

GRANT USAGE ON WAREHOUSE SPOTIFY_WH         TO ROLE SPOTIFY_ROLE;
GRANT USAGE ON DATABASE  SPOTIFY_DB         TO ROLE SPOTIFY_ROLE;
GRANT USAGE ON SCHEMA    SPOTIFY_DB.RAW     TO ROLE SPOTIFY_ROLE;
GRANT USAGE ON SCHEMA    SPOTIFY_DB.STAGING TO ROLE SPOTIFY_ROLE;
GRANT USAGE ON SCHEMA    SPOTIFY_DB.MARTS   TO ROLE SPOTIFY_ROLE;

-- ---------------------------------------------------------------------
-- Set session context for the rest of the script.
-- ---------------------------------------------------------------------
USE WAREHOUSE SPOTIFY_WH;
USE DATABASE  SPOTIFY_DB;
USE SCHEMA    RAW;

-- ---------------------------------------------------------------------
-- Raw tables
--   One table per entity emitted by the extractor. Each table promotes
--   a few scalar columns (the join/filter keys) and keeps the full
--   per-record JSON in `raw_json` for replayable downstream parsing.
--   `_loaded_at` is set by Snowpipe at COPY time for audit.
-- ---------------------------------------------------------------------

-- Tracks: one row per Spotify track in the daily extract.
CREATE TABLE IF NOT EXISTS RAW.TRACKS (
    track_id    VARCHAR,
    track_name  VARCHAR,
    duration_ms INT,
    explicit    BOOLEAN,
    popularity  INT,
    album_id    VARCHAR,
    album_name  VARCHAR,
    raw_json    VARIANT,
    _loaded_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP
);

-- Audio features: one row per track. Derived in the extractor from
-- the track payload (Spotify deprecated /audio-features for new apps
-- in late 2024), so the fields are a subset of the track fields.
CREATE TABLE IF NOT EXISTS RAW.AUDIO_FEATURES (
    track_id    VARCHAR,
    duration_ms INT,
    explicit    BOOLEAN,
    popularity  INT,
    raw_json    VARIANT,
    _loaded_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP
);

-- Artists: one row per unique artist across the day's tracks
-- (deduplicated in the extractor before landing).
CREATE TABLE IF NOT EXISTS RAW.ARTISTS (
    artist_id   VARCHAR,
    artist_name VARCHAR,
    raw_json    VARIANT,
    _loaded_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- File format
--   Each S3 object is a single JSON document ({metadata, data: [...]}),
--   not a bare top-level array, so STRIP_OUTER_ARRAY = FALSE.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FILE FORMAT RAW.SPOTIFY_JSON_FORMAT
    TYPE = JSON
    STRIP_OUTER_ARRAY = FALSE;

-- ---------------------------------------------------------------------
-- External stage
--   Points at the extractor's S3 landing zone. Configure access via a
--   storage integration (preferred — uncomment STORAGE_INTEGRATION
--   below and point it at your provisioned integration), or via inline
--   AWS keys for local/dev use only.
-- ---------------------------------------------------------------------
CREATE STAGE IF NOT EXISTS RAW.SPOTIFY_S3_STAGE
    URL = 's3://spotify-elt-sameer/raw/'
    FILE_FORMAT = RAW.SPOTIFY_JSON_FORMAT
    -- STORAGE_INTEGRATION = SPOTIFY_S3_INTEGRATION
    COMMENT = 'Stage over the Spotify extractor''s S3 raw landing zone';
