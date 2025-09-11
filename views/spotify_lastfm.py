from urllib.parse import quote
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

LASTFM_API_KEY = None

def fetch_tracks_with_genres_and_similar(token, limit=50, lastfm_api_key=None):

    global LASTFM_API_KEY
    LASTFM_API_KEY = lastfm_api_key

    print("🔹 Starting fetch_tracks_with_genres_and_similar")

    
    def spotify_api_get(endpoint, params=None):
        print(f"➡️ Calling Spotify API: {endpoint} with params={params}")
        res = requests.get(
            f"https://api.spotify.com/v1/{endpoint}",
            headers={"Authorization": f"Bearer {token}"},
            params=params
        )
        res.raise_for_status()
        data = res.json()
        print(f"✅ Received {len(data.get('items', []))} items from Spotify API: {endpoint}")
        return data

    
    def format_track(t):
        artist_name = t.get("artists")[0].get("name") if t.get("artists") else ""
        track_info = {
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
        print(f"🎵 Formatted track: {track_info['name']} by {track_info['artist']}")
        return track_info

    
    def get_artist_genres(artist, max_genres=3):
        for attempt in range(3):
            try:
                artist_enc = quote(artist)
                url = f"https://ws.audioscrobbler.com/2.0/?method=artist.getTopTags&artist={artist_enc}&api_key={LASTFM_API_KEY}&format=json"
                res = requests.get(url, timeout=20)
                res.raise_for_status()
                tags = res.json().get("toptags", {}).get("tag", [])
                genres = [t["name"] for t in tags[:max_genres]] if tags else []
                print(f"🎨 Genres for {artist}: {genres}")
                return genres
            except Exception as e:
                print(f"❌ Attempt {attempt + 1} failed for genres {artist}: {e}")
                time.sleep(1)
        print(f"⚠️ Failed to get genres for {artist} after 3 attempts")
        return []

    def get_similar_songs(artist, track, max_similar=3):
        for attempt in range(3):
            try:
                artist_enc = quote(artist)
                track_enc = quote(track)
                url = f"https://ws.audioscrobbler.com/2.0/?method=track.getSimilar&artist={artist_enc}&track={track_enc}&api_key={LASTFM_API_KEY}&format=json&limit={max_similar}"
                res = requests.get(url, timeout=15)
                res.raise_for_status()
                sim_tracks = res.json().get("similartracks", {}).get("track", [])
                if isinstance(sim_tracks, dict):
                    sim_tracks = [sim_tracks]
                similar_list = [{"name": t["name"], "artist": t["artist"]["name"]} for t in sim_tracks[:max_similar]]
                print(f"🔗 Similar songs for {track} by {artist}: {similar_list}")
                return similar_list
            except Exception as e:
                print(f"❌ Attempt {attempt + 1} failed for similar {artist} - {track}: {e}")
                time.sleep(1)
        print(f"⚠️ Failed to get similar songs for {track} by {artist} after 3 attempts")
        return []

    
    top_res = spotify_api_get("me/top/tracks", {"limit": limit})
    recent_res = spotify_api_get("me/player/recently-played", {"limit": limit})

    top_tracks = [format_track(t) for t in top_res.get("items", [])]
    recent_tracks = [format_track(t["track"]) for t in recent_res.get("items", [])]

    all_tracks = top_tracks + recent_tracks

    
    print("🔹 Fetching genres and similar songs concurrently using ThreadPoolExecutor")
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_genres = {executor.submit(get_artist_genres, t["artist"]): t for t in all_tracks}
        future_similar = {executor.submit(get_similar_songs, t["artist"], t["name"]): t for t in all_tracks}

        
        for f in as_completed(future_genres):
            track_obj = future_genres[f]
            try:
                track_obj["genre"] = f.result()
            except Exception as e:
                track_obj["genre"] = []
                print(f"❌ Failed genres for {track_obj['name']}: {e}")

        
        for f in as_completed(future_similar):
            track_obj = future_similar[f]
            try:
                track_obj["similar_songs"] = f.result()
            except Exception as e:
                track_obj["similar_songs"] = []
                print(f"❌ Failed similar songs for {track_obj['name']}: {e}")

    print(f"✅ Finished fetch_tracks_with_genres_and_similar. Total tracks processed: {len(all_tracks)}")
    return top_tracks, recent_tracks