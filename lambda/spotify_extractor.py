"""AWS Lambda function: extract Spotify Global Top 50 data and land raw JSON in S3."""

import json
import logging
import os
from datetime import datetime, timezone

import boto3
import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyClientCredentials

load_dotenv()

logger = logging.getLogger()
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)
logger.setLevel(logging.INFO)

SOURCE = "spotify_api"

# Spotify API per-request limits
SEARCH_PAGE_SIZE = 10
SEARCH_OFFSETS = (0, 10, 20, 30, 40)
SEARCH_QUERY = "genre:pop"
TARGET_TRACK_COUNT = 50

# Editorial playlists (e.g. 37i9dQZEVXbMDoHDwVN2tF "Global Top 50") are no
# longer accessible with SpotifyClientCredentials, so we approximate "trending"
# by searching pop-genre tracks and ranking by Spotify's popularity score.
# Override the market via the SPOTIFY_SEARCH_MARKET env var.
DEFAULT_SEARCH_MARKET = "US"


def _get_spotify_client():
    auth = SpotifyClientCredentials(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
    )
    return spotipy.Spotify(client_credentials_manager=auth)


def _build_s3_key(entity_type, timestamp):
    return (
        f"raw/{entity_type}/"
        f"year={timestamp:%Y}/month={timestamp:%m}/day={timestamp:%d}/"
        f"extract_{timestamp:%Y%m%dT%H%M%SZ}.json"
    )


def _write_to_s3(s3_client, bucket, entity_type, records, timestamp):
    key = _build_s3_key(entity_type, timestamp)
    payload = {
        "metadata": {
            "extraction_timestamp": timestamp.isoformat(),
            "source": SOURCE,
            "record_count": len(records),
        },
        "data": records,
    }
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(payload).encode("utf-8"),
        ContentType="application/json",
    )
    logger.info("Wrote %d %s records to s3://%s/%s", len(records), entity_type, bucket, key)
    return key


def _extract_tracks(sp):
    market = os.environ.get("SPOTIFY_SEARCH_MARKET", DEFAULT_SEARCH_MARKET)

    tracks = []
    for offset in SEARCH_OFFSETS:
        response = sp.search(
            q=SEARCH_QUERY,
            type="track",
            market=market,
            limit=SEARCH_PAGE_SIZE,
            offset=offset,
        )
        tracks.extend((response.get("tracks") or {}).get("items", []))

    tracks.sort(key=lambda t: t.get("popularity", 0), reverse=True)
    return tracks[:TARGET_TRACK_COUNT]


# Spotify deprecated the audio-features and artists batch endpoints for new
# apps in late 2024, so we derive both datasets from fields already present on
# each track returned by sp.search().
def _derive_audio_features(tracks):
    features = []
    for track in tracks:
        if not track:
            continue
        track_id = track.get("id")
        if not track_id:
            continue
        features.append(
            {
                "id": track_id,
                "duration_ms": track.get("duration_ms"),
                "explicit": track.get("explicit"),
                "popularity": track.get("popularity"),
                "available_markets": track.get("available_markets"),
            }
        )
    return features


def _derive_artists(tracks):
    artists_by_id = {}
    for track in tracks:
        if not track:
            continue
        for artist in track.get("artists", []) or []:
            artist_id = artist.get("id")
            if not artist_id or artist_id in artists_by_id:
                continue
            artists_by_id[artist_id] = {
                "id": artist_id,
                "name": artist.get("name"),
            }
    return list(artists_by_id.values())


def handler(event, context):
    timestamp = datetime.now(timezone.utc)
    bucket = os.environ["S3_BUCKET_NAME"]

    sp = _get_spotify_client()
    s3_client = boto3.client("s3", region_name=os.environ.get("AWS_REGION"))

    counts = {"tracks": 0, "audio_features": 0, "artists": 0}

    # Tracks: failure here is fatal — re-raise immediately.
    try:
        tracks = _extract_tracks(sp)
    except Exception:
        logger.error("Failed to extract tracks from Spotify API", exc_info=True)
        raise

    try:
        _write_to_s3(s3_client, bucket, "tracks", tracks, timestamp)
    except Exception:
        logger.error("Failed to write tracks to S3", exc_info=True)
        raise

    counts["tracks"] = len(tracks)

    # Audio features: derived from the track payload — log on S3 failure,
    # continue with partial success.
    features = _derive_audio_features(tracks)
    if features:
        try:
            _write_to_s3(s3_client, bucket, "audio_features", features, timestamp)
            counts["audio_features"] = len(features)
        except Exception:
            logger.error("Failed to write audio features to S3", exc_info=True)

    # Artists: derived from the track payload — log on S3 failure,
    # continue with partial success.
    artists = _derive_artists(tracks)
    if artists:
        try:
            _write_to_s3(s3_client, bucket, "artists", artists, timestamp)
            counts["artists"] = len(artists)
        except Exception:
            logger.error("Failed to write artists to S3", exc_info=True)

    return {
        "statusCode": 200,
        "body": json.dumps(counts),
    }


if __name__ == "__main__":
    result = handler({}, None)
    print(json.dumps(result, indent=2))
