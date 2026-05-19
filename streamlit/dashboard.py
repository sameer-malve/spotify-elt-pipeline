"""Streamlit dashboard for the Spotify ELT pipeline — Spotify-themed."""

import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import snowflake.connector
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Spotify Analytics",
    page_icon="🎵",
    layout="wide",
)

# ---------------------------------------------------------------------
# Theme constants
# ---------------------------------------------------------------------
SPOTIFY_GREEN = "#1DB954"
SPOTIFY_RED = "#E91429"
SPOTIFY_BLACK = "#121212"
CARD_BG = "#181818"
CARD_BORDER = "#282828"
TEXT_PRIMARY = "#FFFFFF"
TEXT_SECONDARY = "#B3B3B3"

PROFILE_COLORS = {
    "Clean Track": SPOTIFY_GREEN,
    "Explicit Track": SPOTIFY_RED,
    "Short Clean": "#B3B3B3",
}

TOP_TRACKS_TABLE = "SPOTIFY_DB.STAGING.MART_TOP_TRACKS"
ARTIST_SUMMARY_TABLE = "SPOTIFY_DB.STAGING.MART_ARTIST_SUMMARY"
STG_TRACKS_TABLE = "SPOTIFY_DB.STAGING.STG_TRACKS"

# ---------------------------------------------------------------------
# Custom CSS — Spotify look & feel
# ---------------------------------------------------------------------
st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {SPOTIFY_BLACK};
        color: {TEXT_PRIMARY};
    }}
    [data-testid="stSidebar"] {{
        background-color: #000000;
        border-right: 1px solid {CARD_BORDER};
    }}
    [data-testid="stSidebar"] * {{
        color: {TEXT_PRIMARY};
    }}
    h1, h2, h3, h4, h5, h6 {{
        color: {TEXT_PRIMARY} !important;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        letter-spacing: -0.01em;
    }}
    .sidebar-logo {{
        color: {SPOTIFY_GREEN};
        font-size: 1.6rem;
        font-weight: 800;
        margin-bottom: 1.25rem;
        letter-spacing: -0.02em;
    }}
    .sidebar-label {{
        color: {TEXT_SECONDARY};
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.25rem;
    }}
    .sidebar-timestamp {{
        color: {SPOTIFY_GREEN};
        font-weight: 700;
        font-size: 1rem;
        margin-bottom: 0.25rem;
    }}
    /* Sidebar buttons */
    [data-testid="stSidebar"] .stButton > button {{
        background-color: {SPOTIFY_GREEN};
        color: #000000;
        border: none;
        border-radius: 500px;
        font-weight: 700;
        letter-spacing: 0.02em;
        transition: transform 0.15s ease;
    }}
    [data-testid="stSidebar"] .stButton > button:hover {{
        background-color: #1ed760;
        transform: scale(1.02);
    }}
    /* Now Playing card */
    .now-playing {{
        background: linear-gradient(135deg, #181818 0%, #232323 100%);
        border: 1px solid {CARD_BORDER};
        border-radius: 12px;
        padding: 1rem 1.5rem;
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 1.5rem;
    }}
    .pulse-dot {{
        width: 12px;
        height: 12px;
        background-color: {SPOTIFY_GREEN};
        border-radius: 50%;
        flex-shrink: 0;
        box-shadow: 0 0 0 0 rgba(29, 185, 84, 0.7);
        animation: pulse 1.5s ease-in-out infinite;
    }}
    @keyframes pulse {{
        0%   {{ box-shadow: 0 0 0 0   rgba(29, 185, 84, 0.7); }}
        70%  {{ box-shadow: 0 0 0 12px rgba(29, 185, 84, 0); }}
        100% {{ box-shadow: 0 0 0 0   rgba(29, 185, 84, 0); }}
    }}
    .now-track {{
        font-size: 1.5rem;
        font-weight: 800;
        color: {TEXT_PRIMARY};
        line-height: 1.1;
        margin-bottom: 0.25rem;
    }}
    .now-artist {{
        font-size: 0.95rem;
        color: {TEXT_SECONDARY};
    }}
    .now-duration {{
        color: {TEXT_SECONDARY};
        font-size: 0.95rem;
        white-space: nowrap;
    }}
    .live-badge {{
        background-color: {SPOTIFY_GREEN};
        color: #000000;
        padding: 0.3rem 0.8rem;
        border-radius: 500px;
        font-size: 0.7rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        white-space: nowrap;
    }}
    /* KPI cards */
    .kpi-card {{
        background-color: {CARD_BG};
        border: 1px solid {CARD_BORDER};
        border-top: 3px solid {SPOTIFY_GREEN};
        border-radius: 8px;
        padding: 1rem 1.1rem;
        height: 100%;
    }}
    .kpi-label {{
        color: {TEXT_SECONDARY};
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 700;
        margin-bottom: 0.4rem;
    }}
    .kpi-value {{
        color: {TEXT_PRIMARY};
        font-size: 1.6rem;
        font-weight: 800;
        line-height: 1.1;
        margin-bottom: 0.2rem;
    }}
    .kpi-sub {{
        color: {TEXT_SECONDARY};
        font-size: 0.8rem;
    }}
    /* Fun fact callouts */
    .fun-fact {{
        background: rgba(29, 185, 84, 0.10);
        border-left: 4px solid {SPOTIFY_GREEN};
        padding: 0.85rem 1rem;
        border-radius: 4px;
        color: {TEXT_PRIMARY};
        margin-bottom: 0.5rem;
        font-size: 0.95rem;
    }}
    /* Section subtitles under subheaders */
    .section-sub {{
        color: {TEXT_SECONDARY};
        font-size: 0.85rem;
        margin-top: -0.5rem;
        margin-bottom: 0.75rem;
    }}
    /* Search results banner */
    .search-result-banner {{
        color: {SPOTIFY_GREEN};
        font-weight: 700;
        margin: 0.5rem 0 0.75rem 0;
    }}
    /* Dataframe — alternating rows hint (Streamlit applies its own theme too) */
    [data-testid="stDataFrame"] {{
        background-color: {CARD_BG};
        border: 1px solid {CARD_BORDER};
        border-radius: 8px;
    }}
    /* Text input */
    .stTextInput > div > div > input {{
        background-color: {CARD_BG};
        color: {TEXT_PRIMARY};
        border: 1px solid {CARD_BORDER};
    }}
    .stTextInput > div > div > input:focus {{
        border-color: {SPOTIFY_GREEN};
    }}
    /* Download button */
    .stDownloadButton > button {{
        background-color: transparent;
        color: {SPOTIFY_GREEN};
        border: 1px solid {SPOTIFY_GREEN};
        border-radius: 500px;
        font-weight: 700;
    }}
    .stDownloadButton > button:hover {{
        background-color: {SPOTIFY_GREEN};
        color: #000000;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------
# Snowflake connection + queries (unchanged contract)
# ---------------------------------------------------------------------
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
    sql = f"""
        SELECT
            t.track_id,
            t.track_name,
            t.duration_ms,
            t.duration_minutes,
            t.is_explicit,
            t.album_id,
            t.album_name,
            t.mood_score,
            t.audio_profile,
            t._loaded_at,
            s.primary_artist_id,
            s.primary_artist_name
        FROM {TOP_TRACKS_TABLE} t
        LEFT JOIN {STG_TRACKS_TABLE} s
            ON t.track_id = s.track_id
    """
    tracks_df = _query(sql)
    tracks_df["duration_minutes"] = pd.to_numeric(tracks_df["duration_minutes"], errors="coerce")
    tracks_df["mood_score"] = pd.to_numeric(tracks_df["mood_score"], errors="coerce")
    tracks_df["_loaded_at"] = pd.to_datetime(tracks_df["_loaded_at"], errors="coerce")
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
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


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
# Sidebar
# ---------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="sidebar-logo">🎵 Spotify Analytics</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-label">Show tracks</div>', unsafe_allow_html=True)
    show_filter = st.radio(
        "Show tracks",
        ["All", "Clean Only", "Explicit Only"],
        label_visibility="collapsed",
    )

    st.markdown('<div class="sidebar-label">Min duration (minutes)</div>', unsafe_allow_html=True)
    min_duration = st.slider(
        "Min duration",
        min_value=1.0,
        max_value=6.0,
        value=1.0,
        step=0.5,
        label_visibility="collapsed",
    )

    if st.button("Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.markdown('<div class="sidebar-label">Last pipeline run</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sidebar-timestamp">{refreshed_at}</div>', unsafe_allow_html=True)
    st.caption("Data refreshed every 24 hours via AWS Lambda + Snowpipe")


# ---------------------------------------------------------------------
# Apply sidebar filters
# ---------------------------------------------------------------------
def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if show_filter == "Clean Only":
        out = out[out["is_explicit"] == False]  # noqa: E712
    elif show_filter == "Explicit Only":
        out = out[out["is_explicit"] == True]  # noqa: E712
    out = out[out["duration_minutes"] >= min_duration]
    return out


filtered_df = apply_filters(tracks_df)


# ---------------------------------------------------------------------
# Section 1 — Now Playing card (uses unfiltered data — pipeline heartbeat)
# ---------------------------------------------------------------------
def _esc(s) -> str:
    if pd.isna(s):
        return ""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


if not tracks_df.empty:
    latest = tracks_df.sort_values("_loaded_at", ascending=False).iloc[0]
    latest_track = _esc(latest.get("track_name", ""))
    latest_artist = _esc(latest.get("primary_artist_name") or "Unknown artist")
    latest_duration = latest.get("duration_minutes")
    duration_str = f"{latest_duration:.2f} min" if pd.notna(latest_duration) else ""

    st.markdown(
        f"""
        <div class="now-playing">
            <div class="pulse-dot"></div>
            <div style="flex-grow:1; min-width:0;">
                <div class="now-track">{latest_track}</div>
                <div class="now-artist">{latest_artist}</div>
            </div>
            <div class="now-duration">{duration_str}</div>
            <div class="live-badge">● LIVE DATA</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------
# Section 2 — KPI row (5 cards)
# ---------------------------------------------------------------------
if not filtered_df.empty:
    total_tracks = len(filtered_df)
    avg_dur = float(filtered_df["duration_minutes"].mean())
    benchmark = 3.5
    if avg_dur > benchmark:
        dur_indicator = "▲"
        dur_color = SPOTIFY_GREEN
        dur_sub = f"▲ {avg_dur - benchmark:.2f} vs {benchmark} min benchmark"
    else:
        dur_indicator = "▼"
        dur_color = SPOTIFY_RED
        dur_sub = f"▼ {benchmark - avg_dur:.2f} vs {benchmark} min benchmark"

    explicit_count = int(filtered_df["is_explicit"].fillna(False).sum())
    explicit_pct = explicit_count / total_tracks * 100
    explicit_color = SPOTIFY_RED if explicit_pct > 30 else SPOTIFY_GREEN
    explicit_sub = f"{'above' if explicit_pct > 30 else 'below'} 30% threshold"

    artist_series = filtered_df["primary_artist_name"].dropna()
    if not artist_series.empty:
        artist_counts = artist_series.value_counts()
        most_artist = artist_counts.index[0]
        most_artist_count = int(artist_counts.iloc[0])
        most_artist_sub = f"{most_artist_count} track{'s' if most_artist_count != 1 else ''}"
    else:
        most_artist = "—"
        most_artist_sub = ""

    longest = filtered_df.loc[filtered_df["duration_minutes"].idxmax()]
    longest_name = str(longest["track_name"])
    longest_dur = float(longest["duration_minutes"])
else:
    total_tracks = 0
    avg_dur = 0.0
    dur_indicator = ""
    dur_color = TEXT_SECONDARY
    dur_sub = ""
    explicit_pct = 0.0
    explicit_color = TEXT_SECONDARY
    explicit_sub = ""
    most_artist = "—"
    most_artist_sub = ""
    longest_name = "—"
    longest_dur = 0.0


def _trunc(s: str, n: int = 28) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">Total Tracks</div>
            <div class="kpi-value">{total_tracks:,}</div>
            <div class="kpi-sub">in today's extract</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with k2:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">Avg Duration</div>
            <div class="kpi-value">{avg_dur:.2f}
                <span style="color:{dur_color}; font-size:1.25rem;">{dur_indicator}</span>
            </div>
            <div class="kpi-sub">{dur_sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with k3:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">Explicit Tracks %</div>
            <div class="kpi-value" style="color:{explicit_color};">{explicit_pct:.0f}%</div>
            <div class="kpi-sub">{explicit_sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with k4:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">Most Represented Artist</div>
            <div class="kpi-value">{_esc(_trunc(most_artist))}</div>
            <div class="kpi-sub">{most_artist_sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with k5:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">Longest Track</div>
            <div class="kpi-value">{_esc(_trunc(longest_name))}</div>
            <div class="kpi-sub">{longest_dur:.2f} min</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------
# Section 3 — Fun Facts bar
# ---------------------------------------------------------------------
if not filtered_df.empty:
    fact_longest = filtered_df.loc[filtered_df["duration_minutes"].idxmax()]
    artist_series = filtered_df["primary_artist_name"].dropna()
    if not artist_series.empty:
        artist_counts = artist_series.value_counts()
        top_artist = artist_counts.index[0]
        top_count = int(artist_counts.iloc[0])
    else:
        top_artist = "Unknown"
        top_count = 0
    explicit_pct_int = round(filtered_df["is_explicit"].fillna(False).sum() / len(filtered_df) * 100)

    facts = [
        f"🎵 Longest track: <strong>{_esc(fact_longest['track_name'])}</strong> at {fact_longest['duration_minutes']:.2f} mins",
        f"🎤 Most featured: <strong>{_esc(top_artist)}</strong> with {top_count} tracks",
        f"🔥 <strong>{explicit_pct_int}%</strong> of today's tracks are explicit",
    ]
    fc1, fc2, fc3 = st.columns(3)
    for col, fact in zip((fc1, fc2, fc3), facts):
        col.markdown(f'<div class="fun-fact">{fact}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------
# Section 4 — Search box (persisted in session_state)
# ---------------------------------------------------------------------
if "search_query" not in st.session_state:
    st.session_state.search_query = ""

st.text_input(
    "Search for a track or artist",
    placeholder="🔍 Search for a track or artist...",
    label_visibility="collapsed",
    key="search_query",
)

search_query = st.session_state.search_query


# ---------------------------------------------------------------------
# Section 5 — Top 20 tracks + Audio profile breakdown
# ---------------------------------------------------------------------
sec5_left, sec5_right = st.columns(2)

with sec5_left:
    st.subheader("Top 20 tracks by duration")
    st.markdown(
        '<div class="section-sub">Longer tracks tend to be cleaner — explicit content skews shorter</div>',
        unsafe_allow_html=True,
    )
    if not filtered_df.empty:
        top20 = filtered_df.nlargest(20, "duration_minutes").sort_values("duration_minutes")
        fig = px.bar(
            top20,
            x="duration_minutes",
            y="track_name",
            color="audio_profile",
            color_discrete_map=PROFILE_COLORS,
            orientation="h",
            hover_data=["primary_artist_name", "album_name", "mood_score"],
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color=TEXT_PRIMARY,
            yaxis_title=None,
            xaxis_title="Duration (minutes)",
            legend_title="Profile",
            height=600,
            margin=dict(t=10, b=40, l=10, r=10),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No tracks match the current filters.")

with sec5_right:
    st.subheader("Audio profile breakdown")
    st.markdown(
        '<div class="section-sub">Most of today\'s top tracks are clean</div>',
        unsafe_allow_html=True,
    )
    if not filtered_df.empty:
        profile_counts = (
            filtered_df.groupby("audio_profile").size().reset_index(name="count")
        )
        total = int(profile_counts["count"].sum())
        profile_counts["pct"] = profile_counts["count"] / total * 100

        fig = go.Figure()
        # Stack in a stable order so colors are consistent
        for profile in ["Clean Track", "Explicit Track", "Short Clean"]:
            row = profile_counts[profile_counts["audio_profile"] == profile]
            if row.empty:
                continue
            pct = float(row["pct"].iloc[0])
            count = int(row["count"].iloc[0])
            fig.add_trace(
                go.Bar(
                    x=[pct],
                    y=["Profile"],
                    orientation="h",
                    name=profile,
                    marker_color=PROFILE_COLORS.get(profile, "#B3B3B3"),
                    text=f"{pct:.0f}%",
                    textposition="inside",
                    insidetextanchor="middle",
                    textfont=dict(color="#000000", size=14),
                    hovertemplate=f"<b>{profile}</b><br>{count} tracks ({pct:.1f}%)<extra></extra>",
                )
            )
        fig.update_layout(
            barmode="stack",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color=TEXT_PRIMARY,
            yaxis=dict(visible=False),
            xaxis=dict(title="% of tracks", range=[0, 100], gridcolor=CARD_BORDER),
            height=180,
            margin=dict(t=10, b=40, l=10, r=10),
            legend=dict(orientation="h", yanchor="bottom", y=-0.8, x=0),
            showlegend=True,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Also surface the raw breakdown numbers below the stacked bar
        breakdown_lines = " · ".join(
            f"<span style='color:{PROFILE_COLORS.get(r['audio_profile'], TEXT_SECONDARY)};'>"
            f"●</span> <strong>{r['audio_profile']}</strong>: {int(r['count'])}"
            for _, r in profile_counts.iterrows()
        )
        st.markdown(
            f"<div style='color:{TEXT_SECONDARY}; margin-top:0.5rem;'>{breakdown_lines}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.info("No tracks match the current filters.")


# ---------------------------------------------------------------------
# Section 6 — Top 10 artists + Duration distribution
# ---------------------------------------------------------------------
sec6_left, sec6_right = st.columns(2)

with sec6_left:
    st.subheader("Top 10 artists by track count")
    st.markdown(
        '<div class="section-sub">Artists with multiple tracks in today\'s extract</div>',
        unsafe_allow_html=True,
    )
    artist_series_full = filtered_df["primary_artist_name"].dropna() if not filtered_df.empty else pd.Series(dtype=str)
    if not artist_series_full.empty:
        artist_top10 = (
            filtered_df.dropna(subset=["primary_artist_name"])
            .groupby("primary_artist_name")
            .size()
            .reset_index(name="track_count")
            .nlargest(10, "track_count")
            .sort_values("track_count")
        )
        fig = px.bar(
            artist_top10,
            x="track_count",
            y="primary_artist_name",
            orientation="h",
        )
        fig.update_traces(marker_color=SPOTIFY_GREEN)
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color=TEXT_PRIMARY,
            yaxis_title=None,
            xaxis_title="Track count",
            height=400,
            margin=dict(t=10, b=40, l=10, r=10),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No artist data available for the current filters.")

with sec6_right:
    st.subheader("Duration distribution")
    st.markdown(
        '<div class="section-sub">Most popular tracks cluster around 3-4 minutes</div>',
        unsafe_allow_html=True,
    )
    if not filtered_df.empty:
        fig = px.histogram(
            filtered_df,
            x="duration_minutes",
            color="audio_profile",
            color_discrete_map=PROFILE_COLORS,
        )
        fig.update_traces(xbins=dict(size=0.5))
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color=TEXT_PRIMARY,
            xaxis_title="Duration (minutes, 30-second bins)",
            yaxis_title="Track count",
            legend_title="Profile",
            height=400,
            bargap=0.05,
            margin=dict(t=10, b=40, l=10, r=10),
            xaxis=dict(gridcolor=CARD_BORDER),
            yaxis=dict(gridcolor=CARD_BORDER),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No tracks match the current filters.")


# ---------------------------------------------------------------------
# Section 7 — Scatter (full width)
# ---------------------------------------------------------------------
st.subheader("Explicit vs Clean: Duration vs Mood Score")
st.markdown(
    '<div class="section-sub">Clean tracks score higher on mood — explicit tracks tend to be shorter and punchier</div>',
    unsafe_allow_html=True,
)
if not filtered_df.empty:
    fig = px.scatter(
        filtered_df,
        x="duration_minutes",
        y="mood_score",
        color="audio_profile",
        color_discrete_map=PROFILE_COLORS,
        hover_data=["track_name", "primary_artist_name", "album_name"],
    )
    fig.add_vline(
        x=3.5,
        line_dash="dash",
        line_color=TEXT_SECONDARY,
        annotation_text="Avg duration",
        annotation_position="top",
        annotation_font_color=TEXT_SECONDARY,
    )
    fig.update_traces(marker=dict(size=11, line=dict(width=1, color=SPOTIFY_BLACK)))
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color=TEXT_PRIMARY,
        xaxis_title="Duration (minutes)",
        yaxis_title="Mood score",
        legend_title="Profile",
        height=500,
        margin=dict(t=10, b=40, l=10, r=10),
        xaxis=dict(gridcolor=CARD_BORDER),
        yaxis=dict(gridcolor=CARD_BORDER),
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No tracks match the current filters.")


# ---------------------------------------------------------------------
# Section 8 — Track table (full width)
# ---------------------------------------------------------------------
st.subheader("All Tracks Today")

table_source = filtered_df.copy()
query = (search_query or "").strip()
if query:
    q = query.lower()
    track_mask = table_source["track_name"].fillna("").str.lower().str.contains(q, regex=False)
    artist_mask = (
        table_source["primary_artist_name"].fillna("").str.lower().str.contains(q, regex=False)
    )
    table_source = table_source[track_mask | artist_mask]
    st.markdown(
        f'<div class="search-result-banner">{len(table_source)} results found for "{_esc(query)}"</div>',
        unsafe_allow_html=True,
    )

display_df = (
    table_source[
        [
            "track_name",
            "primary_artist_name",
            "duration_minutes",
            "audio_profile",
            "mood_score",
        ]
    ]
    .rename(
        columns={
            "track_name": "Track",
            "primary_artist_name": "Artist",
            "duration_minutes": "Duration (min)",
            "audio_profile": "Profile",
            "mood_score": "Mood Score",
        }
    )
    .reset_index(drop=True)
)

csv_bytes = display_df.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇ Download as CSV",
    data=csv_bytes,
    file_name="spotify_tracks.csv",
    mime="text/csv",
)


def _row_stripes(row: pd.Series):
    bg = "#1c1c1c" if row.name % 2 == 0 else CARD_BG
    return [f"background-color: {bg}; color: {TEXT_PRIMARY};"] * len(row)


styled = (
    display_df.style.apply(_row_stripes, axis=1)
    .format({"Duration (min)": "{:.2f}", "Mood Score": "{:.4f}"})
    .set_table_styles(
        [
            {"selector": "th", "props": [
                ("background-color", CARD_BG),
                ("color", TEXT_SECONDARY),
                ("text-transform", "uppercase"),
                ("font-size", "0.75rem"),
                ("letter-spacing", "0.05em"),
            ]},
        ]
    )
)

st.dataframe(styled, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------
st.divider()
st.caption(f"Last refreshed: {refreshed_at}")
