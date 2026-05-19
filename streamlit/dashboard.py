"""Streamlit dashboard for the Spotify ELT pipeline."""

import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import snowflake.connector
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Spotify Analytics",
    layout="wide",
)

TOP_TRACKS_TABLE = "SPOTIFY_DB.STAGING.MART_TOP_TRACKS"
ARTIST_SUMMARY_TABLE = "SPOTIFY_DB.STAGING.MART_ARTIST_SUMMARY"


@st.cache_resource
def _get_connection():
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        database=os.environ["SNOWFLAKE_DATABASE"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        role=os.environ["SNOWFLAKE_ROLE"],
    )


def _query(sql: str) -> pd.DataFrame:
    conn = _get_connection()
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
        columns = [c[0].lower() for c in cur.description]
    return pd.DataFrame(rows, columns=columns)


@st.cache_data(ttl=3600)
def load_top_tracks() -> pd.DataFrame:
    tracks_df = _query(f"SELECT * FROM {TOP_TRACKS_TABLE}")
    tracks_df["duration_minutes"] = pd.to_numeric(tracks_df["duration_minutes"], errors="coerce")
    tracks_df["mood_score"] = pd.to_numeric(tracks_df["mood_score"], errors="coerce")
    return tracks_df


@st.cache_data(ttl=3600)
def load_artist_summary() -> pd.DataFrame:
    artists_df = _query(f"SELECT * FROM {ARTIST_SUMMARY_TABLE}")
    artists_df["track_count"] = pd.to_numeric(artists_df["track_count"], errors="coerce")
    artists_df["avg_duration_minutes"] = pd.to_numeric(artists_df["avg_duration_minutes"], errors="coerce")
    artists_df["total_explicit_tracks"] = pd.to_numeric(artists_df["total_explicit_tracks"], errors="coerce")
    return artists_df


@st.cache_data(ttl=3600)
def load_refresh_timestamp() -> str:
    # Cached alongside the data, so it advances only when the cache is cleared.
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------
with st.sidebar:
    st.header("Controls")
    if st.button("Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.caption(
        "Data is cached for 1 hour. Use **Refresh Data** to force a "
        "re-query against Snowflake."
    )

# ---------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------
st.title("Spotify Analytics Dashboard")
st.caption("Real-time insights from Spotify's top tracks")

# ---------------------------------------------------------------------
# Data load (with graceful connection-error handling)
# ---------------------------------------------------------------------
try:
    tracks_df = load_top_tracks()
    artists_df = load_artist_summary()
    refreshed_at = load_refresh_timestamp()
except Exception as exc:
    st.error(f"Failed to load data from Snowflake: {exc}")
    st.stop()

# ---------------------------------------------------------------------
# KPI row
# ---------------------------------------------------------------------
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

kpi1.metric("Total Tracks", f"{len(tracks_df):,}")

avg_duration = tracks_df["duration_minutes"].mean() if not tracks_df.empty else None
kpi2.metric(
    "Avg Duration (minutes)",
    f"{avg_duration:.2f}" if avg_duration is not None else "—",
)

if not tracks_df.empty:
    most_common_profile = tracks_df["audio_profile"].mode().iloc[0]
else:
    most_common_profile = "—"
kpi3.metric("Most Common Audio Profile", most_common_profile)

kpi4.metric("Total Artists", f"{len(artists_df):,}")

st.divider()

# ---------------------------------------------------------------------
# Chart 1 — Top 20 tracks by duration (horizontal bar)
# ---------------------------------------------------------------------
st.subheader("Top 20 tracks by duration")
top20 = tracks_df.nlargest(20, "duration_minutes")
fig_tracks = px.bar(
    top20.sort_values("duration_minutes"),
    x="duration_minutes",
    y="track_name",
    color="audio_profile",
    orientation="h",
    hover_data=["album_name", "mood_score"],
)
fig_tracks.update_layout(
    yaxis_title=None,
    xaxis_title="Duration (minutes)",
    legend_title="Audio profile",
    height=600,
)
st.plotly_chart(fig_tracks, use_container_width=True)

# ---------------------------------------------------------------------
# Chart 2 — Audio profile distribution (pie)
# ---------------------------------------------------------------------
st.subheader("Audio profile distribution")
profile_counts = (
    tracks_df.groupby("audio_profile")
    .size()
    .reset_index(name="count")
    .sort_values("count", ascending=False)
)
fig_profile = px.pie(
    profile_counts,
    names="audio_profile",
    values="count",
    hole=0.4,
)
st.plotly_chart(fig_profile, use_container_width=True)

# ---------------------------------------------------------------------
# Chart 3 — Top 10 artists by track count (horizontal bar)
# ---------------------------------------------------------------------
st.subheader("Top 10 artists by track count")
top10_artists = artists_df.nlargest(10, "track_count")
fig_artists = px.bar(
    top10_artists.sort_values("track_count"),
    x="track_count",
    y="artist_name",
    orientation="h",
    hover_data=["avg_duration_minutes", "total_explicit_tracks"],
)
fig_artists.update_layout(
    yaxis_title=None,
    xaxis_title="Track count",
    height=500,
)
st.plotly_chart(fig_artists, use_container_width=True)

# ---------------------------------------------------------------------
# Chart 4 — Explicit vs Clean tracks (scatter)
# ---------------------------------------------------------------------
st.subheader("Explicit vs Clean tracks")
fig_scatter = px.scatter(
    tracks_df,
    x="duration_minutes",
    y="mood_score",
    color="audio_profile",
    hover_data=["track_name", "album_name"],
)
fig_scatter.update_layout(
    xaxis_title="Duration (minutes)",
    yaxis_title="Mood score",
    legend_title="Audio profile",
)
st.plotly_chart(fig_scatter, use_container_width=True)

# ---------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------
st.divider()
st.caption(f"Last refreshed: {refreshed_at}")
