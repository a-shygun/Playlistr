

from urllib.parse import quote
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

def fetch_tracks_with_genres_and_similar(token, limit=50, lastfm_api_key=None):
    def spotify_api_get(endpoint, params=None):
        res = requests.get(
            f"https://api.spotify.com/v1/{endpoint}",
            headers={"Authorization": f"Bearer {token}"},
            params=params
        )
        res.raise_for_status()
        return res.json()

    def format_track(t):
        artist_name = t.get("artists")[0]["name"] if t.get("artists") else ""
        return {
            "name": t.get("name"),
            "artist": artist_name,
            "artist_url": t.get("artists")[0].get("external_urls", {}).get("spotify", "") if t.get("artists") else "",
            "album": t.get("album", {}).get("name", ""),
            "album_url": t.get("album", {}).get("external_urls", {}).get("spotify", ""),
            "img": t.get("album", {}).get("images", [{}])[0].get("url", ""),
            "url": t.get("external_urls", {}).get("spotify", ""),
            "genre": [],
            "rank": None,
            "similar_songs": []
        }

    def get_artist_genres(artist, max_genres=3):
        for _ in range(3):
            try:
                url = f"https://ws.audioscrobbler.com/2.0/?method=artist.getTopTags&artist={quote(artist)}&api_key={lastfm_api_key}&format=json"
                res = requests.get(url, timeout=20)
                res.raise_for_status()
                tags = res.json().get("toptags", {}).get("tag", [])
                return [t["name"] for t in tags[:max_genres]] if tags else []
            except:
                time.sleep(1)
        return []

    def get_similar_songs(artist, track, max_similar=3):
        for _ in range(3):
            try:
                url = f"https://ws.audioscrobbler.com/2.0/?method=track.getSimilar&artist={quote(artist)}&track={quote(track)}&api_key={lastfm_api_key}&format=json&limit={max_similar}"
                res = requests.get(url, timeout=15)
                res.raise_for_status()
                sim_tracks = res.json().get("similartracks", {}).get("track", [])
                if isinstance(sim_tracks, dict):
                    sim_tracks = [sim_tracks]
                return [{"name": t["name"], "artist": t["artist"]["name"]} for t in sim_tracks[:max_similar]]
            except:
                time.sleep(1)
        return []

    top_res = spotify_api_get("me/top/tracks", {"limit": limit})
    recent_res = spotify_api_get("me/player/recently-played", {"limit": limit})

    top_tracks = [format_track(t) for t in top_res.get("items", [])]
    recent_tracks = [format_track(t["track"]) for t in recent_res.get("items", [])]
    all_tracks = top_tracks + recent_tracks

    with ThreadPoolExecutor(max_workers=10) as executor:
        future_genres = {executor.submit(get_artist_genres, t["artist"]): t for t in all_tracks}
        future_similar = {executor.submit(get_similar_songs, t["artist"], t["name"]): t for t in all_tracks}

        for f in as_completed(future_genres):
            try:
                future_genres[f]["genre"] = f.result()
            except:
                future_genres[f]["genre"] = []

        for f in as_completed(future_similar):
            try:
                future_similar[f]["similar_songs"] = f.result()
            except:
                future_similar[f]["similar_songs"] = []

    return top_tracks, recent_tracks