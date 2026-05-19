# spotify-elt-pipeline

A production-grade ELT pipeline that extracts data from the Spotify Web API,
lands raw payloads in S3, ingests them into Snowflake via Snowpipe, transforms
them with dbt, orchestrates the workflow with Airflow, and surfaces the results
in a Streamlit dashboard.

## Architecture

> _Placeholder — see [`docs/architecture.md`](docs/architecture.md) for the full
> diagram and component breakdown._

High-level flow:

1. **Extract** — AWS Lambda calls the Spotify API on a schedule.
2. **Load** — Raw JSON is written to S3 and auto-ingested into Snowflake via Snowpipe.
3. **Transform** — dbt models build `staging` → `intermediate` → `marts` layers.
4. **Orchestrate** — Airflow DAG (`airflow/dags/spotify_elt_dag.py`) coordinates the run.
5. **Visualize** — Streamlit app (`streamlit/dashboard.py`) reads from the marts.

## Getting Started

1. **Clone & configure environment**

   Copy the example environment file and fill in your own values:

   ```bash
   cp .env.example .env
   ```

   The required variables are listed in [`.env.example`](.env.example).

2. **Install Python dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure dbt**

   ```bash
   cp dbt/profiles.yml.example dbt/profiles.yml
   ```

4. **Start the local Airflow stack**

   ```bash
   docker-compose up airflow-init
   docker-compose up
   ```

   The Airflow UI is then available at <http://localhost:8080>.

5. **Run the dashboard**

   ```bash
   streamlit run streamlit/dashboard.py
   ```

## Project layout

```
spotify-elt-pipeline/
├── lambda/        # Spotify API extractor (AWS Lambda)
├── snowflake/     # DDL + Snowpipe setup
├── dbt/           # dbt project (staging / intermediate / marts)
├── airflow/       # DAGs and plugins
├── streamlit/     # Dashboard app
└── docs/          # Architecture & design docs
```
