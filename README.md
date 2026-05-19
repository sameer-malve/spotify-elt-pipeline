# Spotify Analytics ELT Pipeline

End-to-end ELT pipeline that extracts Spotify track data, transforms it through a Snowflake + dbt model layer, and delivers a live analytics dashboard via Streamlit.

[![Live Dashboard](https://img.shields.io/badge/Live%20Dashboard-Open-FF4B4B?logo=streamlit&logoColor=white)](https://spotify-elt-pipeline-rjdnqjgqdmzgyfgm4vt9ny.streamlit.app)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Apache Airflow](https://img.shields.io/badge/Apache%20Airflow-2.8-017CEE?logo=apacheairflow&logoColor=white)](https://airflow.apache.org/)
[![dbt-snowflake](https://img.shields.io/badge/dbt--snowflake-FF694B?logo=dbt&logoColor=white)](https://docs.getdbt.com/docs/core/connect-data-platform/snowflake-setup)
[![AWS Lambda](https://img.shields.io/badge/AWS-Lambda-FF9900?logo=awslambda&logoColor=white)](https://aws.amazon.com/lambda/)
[![Snowflake](https://img.shields.io/badge/Snowflake-29B5E8?logo=snowflake&logoColor=white)](https://www.snowflake.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)

---

## Architecture

The pipeline extracts trending Spotify tracks daily via an AWS Lambda function calling the Spotify Web API with client-credentials auth. Raw JSON payloads are written to S3 under a date-partitioned prefix, where Snowpipe auto-ingests them into Snowflake's `RAW` schema the moment new files land. dbt then transforms `RAW` into typed `STAGING` views and finally into `MARTS` tables, applying deduplication, type casting, and derived metrics such as `mood_score` and `audio_profile`. Streamlit reads the marts directly and renders a public live dashboard.

```
Spotify API → AWS Lambda → AWS S3 → Snowpipe → Snowflake RAW
                                                      ↓
                                                   dbt (Staging → Marts)
                                                      ↓
                                              Streamlit Dashboard (Live)
```

---

## Tech Stack

| Layer | Tool | Purpose |
|---|---|---|
| Extraction | Python + Spotipy + AWS Lambda | Pulls top 50 tracks from Spotify API daily |
| Storage | AWS S3 | Raw JSON data lake partitioned by date |
| Auto-ingestion | Snowpipe | Event-driven loading from S3 to Snowflake on file arrival |
| Warehouse | Snowflake | Cloud data warehouse with RAW, STAGING, MARTS schemas |
| Transformation | dbt-snowflake | Staging views + mart tables with data quality tests |
| Orchestration | Apache Airflow | Daily pipeline scheduling and monitoring |
| Visualization | Streamlit + Plotly | Live public dashboard |
| Version Control | GitHub | Source code and CI |

---

## Key Features

- **Live Streamlit dashboard** with 4 interactive charts — publicly accessible at the link above.
- **Snowpipe auto-ingestion** triggers automatically when new files land in S3 (no polling, no batch job).
- **dbt data quality tests** run on every model — 10/10 tests passing.
- **Medallion-style layering**: RAW events → STAGING views → MART tables.
- **Deduplication logic** in staging models using `ROW_NUMBER()` to handle multiple pipeline runs against the same source data.
- **Audio profile classification** (`Explicit Track` / `Clean Track` / `Short Clean`) derived from track metadata.
- **Mood score** calculated per track combining duration and the explicit flag.

---

## Dashboard

**Live:** <https://spotify-elt-pipeline-rjdnqjgqdmzgyfgm4vt9ny.streamlit.app>

Built with Streamlit + Plotly, connected directly to the Snowflake `STAGING` schema.

The dashboard renders four charts:

1. **Top 20 tracks by duration** — horizontal bar chart, colored by audio profile, showing which tracks run longest in the daily extract.
2. **Audio profile distribution** — donut chart breaking down the share of `Explicit Track` / `Clean Track` / `Short Clean` across the catalog.
3. **Top 10 artists by track count** — horizontal bar chart ranking primary artists by how many tracks they appear on.
4. **Explicit vs Clean tracks** — scatter plot of `duration_minutes` vs `mood_score`, colored by audio profile, revealing how length and explicit flag interact.

---

## Project Structure

```
spotify-elt-pipeline/
├── .env.example
├── .gitignore
├── README.md
├── docker-compose.yml
├── requirements.txt
├── lambda/
│   ├── spotify_extractor.py        # AWS Lambda: Spotify API → S3
│   └── requirements.txt
├── snowflake/
│   ├── setup.sql                   # Database, schemas, warehouse, role, raw tables, stage
│   └── snowpipe.sql                # Auto-ingest pipes per entity
├── dbt/
│   ├── dbt_project.yml
│   ├── profiles.yml.example
│   ├── models/
│   │   ├── staging/
│   │   │   ├── sources.yml
│   │   │   ├── schema.yml
│   │   │   ├── stg_tracks.sql
│   │   │   ├── stg_audio_features.sql
│   │   │   └── stg_artists.sql
│   │   └── marts/
│   │       ├── schema.yml
│   │       ├── mart_top_tracks.sql
│   │       └── mart_artist_summary.sql
│   ├── tests/
│   └── macros/
├── airflow/
│   ├── dags/
│   │   └── spotify_elt_dag.py
│   └── plugins/
├── streamlit/
│   ├── dashboard.py                # Live dashboard
│   └── requirements.txt
└── docs/
    └── architecture.md
```

---

## Getting Started

### Prerequisites

- Python **3.13** (3.14 is not yet supported by `dbt-snowflake` — see [What I learned](#what-i-learned)).
- A Spotify developer app (Client ID + Client Secret).
- An AWS account with an S3 bucket and an IAM role for Lambda execution.
- A Snowflake account with permission to create databases, warehouses, and storage integrations.

### Setup

1. **Clone the repo**

   ```bash
   git clone https://github.com/<your-username>/spotify-elt-pipeline.git
   cd spotify-elt-pipeline
   ```

2. **Configure environment variables**

   ```bash
   cp .env.example .env
   # then fill in your own values
   ```

   See [`.env.example`](.env.example) for the full list (Spotify, AWS, Snowflake, dbt).

3. **Install Python dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Provision Snowflake**

   Run the setup scripts (idempotent) against your Snowflake account:

   ```bash
   snowsql -f snowflake/setup.sql
   snowsql -f snowflake/snowpipe.sql
   ```

5. **Run the extractor locally**

   ```bash
   python lambda/spotify_extractor.py
   ```

   This pulls the latest tracks and writes raw JSON to `s3://<your-bucket>/raw/...`. Snowpipe will auto-ingest within ~1 minute.

6. **Run dbt**

   ```bash
   cp dbt/profiles.yml.example dbt/profiles.yml
   cd dbt
   dbt run  --profiles-dir .
   dbt test --profiles-dir .
   ```

7. **Launch the dashboard locally**

   ```bash
   streamlit run streamlit/dashboard.py
   ```

---

## dbt Models

```
Sources (RAW schema)
└── V_TRACKS, V_AUDIO_FEATURES, V_ARTISTS
    ↓
Staging (views)
└── stg_tracks, stg_audio_features, stg_artists
    ↓
Marts (tables)
└── mart_top_tracks, mart_artist_summary
```

Run `dbt docs generate && dbt docs serve` to view the full interactive lineage graph.

---

## What I learned

- **Snowpipe auto-ingestion requires a storage integration IAM role** set up between AWS and Snowflake — not just S3 event notifications. The S3 → SQS → Snowpipe chain only works once Snowflake's external ID is trusted by the IAM role.
- **Spotify deprecated audio features and batch artist endpoints for new apps in late 2024.** Adapted the extractor to derive metrics (`duration_ms`, `explicit`, popularity-like attributes, and artist references) from fields already present in the `/search` response, removing all dependencies on the deprecated endpoints.
- **dbt deduplication using `ROW_NUMBER()` is essential** when running pipelines multiple times in development. Re-running the extractor against the same window writes new S3 files, and without `ROW_NUMBER() OVER (PARTITION BY id ORDER BY _loaded_at DESC)` the `unique` tests on staging models fail immediately.
- **Python 3.14 is not yet compatible with `dbt-snowflake`** — pin the runtime to Python 3.13 across the extractor, dbt, and the Streamlit app to avoid resolver errors.
