import pycountry
import json
import os
import pandas as pd
import requests
from xml.etree import ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from flask import session


def id_header_col_info():
    user_info = session.get('user_info')
    user_id = user_info.get('id') if user_info else None

    access_token = session.get("access_token")
    headers = {"Authorization": f"Bearer {access_token}"}

    fieldnames = ["playlist", "name", "name_url", "artist",
                  "album", "year", "album_art"]

    return user_id, headers, fieldnames

def fetch_user_info():
    print("[DataEDA] Fetching user info from Spotify...")
    _, headers, fieldnames = id_header_col_info()
    url = "https://api.spotify.com/v1/me"
    try:
        res = requests.get(url, headers=headers, timeout=30)
        res.raise_for_status()
        data = res.json()

        country_code = data.get("country")
        country_name = pycountry.countries.get(alpha_2=country_code).name if country_code else None
        images = data.get("images") or []
        img_url = images[0].get("url") if images else ""
        session['user_info'] = {
            "name": data.get("display_name"),
            "email": data.get("email"),
            "img": img_url,
            "country": country_name,
            "product": data.get("product"),
            "spotify_link": data.get("external_urls", {}).get("spotify", ""),
            "id": data.get("id")
        }
        print(f"[DataEDA] Fetched user info for {session['user_info']['name']} ({session['user_info']['id']})")

    except Exception as e:
        print(f"[DataEDA] Failed to fetch user details: {e}")
        raise

def save_user_info():
    user_id = session.get("user_info").get("id")
    datasets_dir = os.path.join("temp", user_id, "datasets")
    print(f"[DataEDA] Saving user info to {datasets_dir}...")
    user_info_file = os.path.join(datasets_dir, "user_info.json")
    with open(user_info_file, "w") as f:
        json.dump(session['user_info'], f, indent=4)
    print(f"[DataEDA] User info saved to {user_info_file}")


def fetch_save_user_tracks():
    user_id, headers, fieldnames = id_header_col_info()
    print("[DataEDA] Fetching user playlists from Spotify...")
    playlists = []
    next_url = "https://api.spotify.com/v1/me/playlists?limit=50"

    while next_url:
        res = requests.get(next_url, headers=headers)
        res.raise_for_status()
        data = res.json()
        playlists.extend(data.get("items", []))
        next_url = data.get("next")

    total_playlists = len(playlists)
    total_playlist_tracks = sum(pl.get("tracks", {}).get("total", 0) for pl in playlists)
    session['user_info']['total_playlists'] = total_playlists
    session['user_info']['total_tracks'] = total_playlist_tracks
    print(f"[DataEDA] Found {total_playlists} playlists with {total_playlist_tracks} total tracks")

    def fetch_tracks(pl):
        tracks = []
        pl_name = pl.get("name", "Unnamed Playlist")
        url = pl["tracks"]["href"]
        while url:
            res = requests.get(url, headers=headers)
            res.raise_for_status()
            data = res.json()

            for item in data.get("items", []):
                t = item.get("track")
                if not t:
                    continue
                artist = t.get("artists", [{}])[0].get("name", "")
                album = t.get("album", {})
                release_date = album.get("release_date", "1900")
                year = int(release_date[:4]) if release_date else 1900
                album_images = album.get("images", [{}])
                album_art = album_images[0].get("url", "")

                tracks.append({
                    "playlist": pl_name,
                    "name": t.get("name", ""),
                    "name_url": t.get("external_urls", {}).get("spotify", ""),
                    "artist": artist,
                    "album": album.get("name", ""),
                    "year": year,
                    "album_art": album_art,
                })

            url = data.get("next")
        print(f"[DataEDA] {pl_name}: collected {len(tracks)} tracks")
        return tracks

    all_tracks = []
    print("[DataEDA] Fetching tracks from all playlists concurrently...")
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_tracks, pl): pl.get("name", "Unnamed Playlist") for pl in playlists}
        for f in as_completed(futures):
            try:
                all_tracks.extend(f.result())
            except Exception as e:
                print(f"[DataEDA] Error fetching playlist '{futures[f]}': {e}")

    datasets_dir = os.path.join("temp", user_id, "datasets")
    os.makedirs(datasets_dir, exist_ok=True)
    csv_file = os.path.join(datasets_dir, "user_songs.csv")

    print(f"[DataEDA] Saving all tracks to {csv_file}...")
    df = pd.DataFrame(all_tracks, columns=fieldnames)
    df.to_csv(csv_file, index=False)
    print(f"[DataEDA] Saved {len(all_tracks)} tracks to {csv_file}")


def fetch_save_top_tracks():
    user_id, headers, fieldnames = id_header_col_info()

    url = f"https://api.spotify.com/v1/me/top/tracks?limit=50"

    res = requests.get(url, headers=headers)
    res.raise_for_status()
    data = res.json()

    top_tracks = []
    for t in data.get("items", []):
        artist_name = t["artists"][0]["name"] if t.get("artists") else ""
        release_date = t.get("album", {}).get("release_date", "1900")
        year = int(release_date[:4]) if release_date else 1900

        track_info = {
            "playlist": "Top Tracks",
            "name": t.get("name"),
            "name_url": t.get("external_urls", {}).get("spotify", ""),
            "artist": artist_name,
            "artist_url": t.get("artists")[0].get("external_urls", {}).get("spotify", "") if t.get("artists") else "",
            "album": t.get("album", {}).get("name", ""),
            "album_url": t.get("album", {}).get("external_urls", {}).get("spotify", ""),
            "year": year,
            "album_art": t.get("album", {}).get("images", [{}])[0].get("url", ""),
            "genres": "",
            "similar_songs": ""
        }
        top_tracks.append(track_info)

    datasets_dir = os.path.join("temp", user_id, "datasets")
    csv_file = os.path.join(datasets_dir, "top_tracks.csv")

    df = pd.DataFrame(top_tracks, columns=fieldnames)
    df.to_csv(csv_file, index=False)

    print(f"[DataEDA] Saved {len(top_tracks)} top tracks to {csv_file}")

def fetch_save_recent_tracks():
    user_id, headers, fieldnames = id_header_col_info()
    url = f"https://api.spotify.com/v1/me/player/recently-played?limit=50"

    res = requests.get(url, headers=headers)
    res.raise_for_status()
    data = res.json()

    recent_tracks = []
    for item in data.get("items", []):
        t = item.get("track")
        if not t:
            continue
        artist_name = t.get("artists", [{}])[0].get("name", "")
        album = t.get("album", {})
        release_date = album.get("release_date", "1900")
        year = int(release_date[:4]) if release_date else 1900
        album_art = album.get("images", [{}])[0].get("url", "")

        track_info = {
            "playlist": "Recent Tracks",
            "name": t.get("name", ""),
            "name_url": t.get("external_urls", {}).get("spotify", ""),
            "artist": artist_name,
            "artist_url": t.get("artists", [{}])[0].get("external_urls", {}).get("spotify", ""),
            "album": album.get("name", ""),
            "album_url": album.get("external_urls", {}).get("spotify", ""),
            "year": year,
            "album_art": album_art,
            "genres": "",
            "similar_songs": ""
        }
        recent_tracks.append(track_info)

    datasets_dir = os.path.join("temp", str(user_id), "datasets")
    csv_file = os.path.join(datasets_dir, "recent_tracks.csv")

    df = pd.DataFrame(recent_tracks, columns=fieldnames)
    df.to_csv(csv_file, index=False)

    print(f"[DataEDA] Saved {len(recent_tracks)} recent tracks to {csv_file}")


def fetch_save_top_tracks():
    user_id, headers, fieldnames = id_header_col_info()
    print("[DataEDA] Fetching top tracks from Spotify...")

    url = "https://api.spotify.com/v1/me/top/tracks?limit=50"
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    data = res.json()

    top_tracks = []
    for t in data.get("items", []):
        artist_name = t.get("artists", [{}])[0].get("name", "")
        album = t.get("album", {})
        release_date = album.get("release_date", "1900")
        year = int(release_date[:4]) if release_date else 1900
        album_art = album.get("images", [{}])[0].get("url", "")

        track_info = {
            "playlist": "Top Tracks",
            "name": t.get("name", ""),
            "name_url": t.get("external_urls", {}).get("spotify", ""),
            "artist": artist_name,
            "artist_url": t.get("artists", [{}])[0].get("external_urls", {}).get("spotify", ""),
            "album": album.get("name", ""),
            "album_url": album.get("external_urls", {}).get("spotify", ""),
            "year": year,
            "album_art": album_art,
            "genres": "",
            "similar_songs": ""
        }
        top_tracks.append(track_info)

    datasets_dir = os.path.join("temp", str(user_id), "datasets")
    os.makedirs(datasets_dir, exist_ok=True)
    csv_file = os.path.join(datasets_dir, "top_tracks.csv")

    df = pd.DataFrame(top_tracks, columns=fieldnames)
    df.to_csv(csv_file, index=False)
    print(f"[DataEDA] Saved {len(top_tracks)} top tracks to {csv_file}")

def fetch_save_recent_tracks():
    user_id, headers, fieldnames = id_header_col_info()
    print("[DataEDA] Fetching recently played tracks from Spotify...")

    url = "https://api.spotify.com/v1/me/player/recently-played?limit=50"
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    data = res.json()

    recent_tracks = []
    for item in data.get("items", []):
        t = item.get("track")
        if not t:
            continue
        artist_name = t.get("artists", [{}])[0].get("name", "")
        album = t.get("album", {})
        release_date = album.get("release_date", "1900")
        year = int(release_date[:4]) if release_date else 1900
        album_art = album.get("images", [{}])[0].get("url", "")

        track_info = {
            "playlist": "Recent Tracks",
            "name": t.get("name", ""),
            "name_url": t.get("external_urls", {}).get("spotify", ""),
            "artist": artist_name,
            "artist_url": t.get("artists", [{}])[0].get("external_urls", {}).get("spotify", ""),
            "album": album.get("name", ""),
            "album_url": album.get("external_urls", {}).get("spotify", ""),
            "year": year,
            "album_art": album_art,
            "genres": "",
            "similar_songs": ""
        }
        recent_tracks.append(track_info)

    datasets_dir = os.path.join("temp", str(user_id), "datasets")
    os.makedirs(datasets_dir, exist_ok=True)
    csv_file = os.path.join(datasets_dir, "recent_tracks.csv")

    df = pd.DataFrame(recent_tracks, columns=fieldnames)
    df.to_csv(csv_file, index=False)
    print(f"[DataEDA] Saved {len(recent_tracks)} recent tracks to {csv_file}")



def enrich_songs_with_lastfm(lastfm_api_key, max_workers=8, retry_count=3, backoff=2):
    user_id = session.get("user_info").get("id")
    datasets_dir = os.path.join("temp", user_id, "datasets")
    csv_files = ["user_songs.csv", "top_tracks.csv", "recent_tracks.csv"]

    dfs = {}
    for f in csv_files:
        path = os.path.join(datasets_dir, f)
        if os.path.exists(path):
            dfs[f] = pd.read_csv(path)

    if not dfs:
        print("[DataEDA] No CSVs found. Exiting.")
        return

    unique_artists = pd.concat([df["artist"].dropna() for df in dfs.values()]).unique()
    print(f"[DataEDA] Fetching Last.fm info for {len(unique_artists)} unique artists...")

    artist_cache = {}

    def fetch_artist_info(artist_name):
        if artist_name in artist_cache:
            return artist_cache[artist_name]

        url = f"http://ws.audioscrobbler.com/2.0/?method=artist.getInfo&artist={artist_name}&api_key={lastfm_api_key}&format=xml"
        for attempt in range(retry_count):
            try:
                res = requests.get(url, timeout=10)
                res.raise_for_status()
                root = ET.fromstring(res.text)
                genres = [t.find("name").text for t in root.findall(".//tags/tag")][:3] if root.find(".//tags") else []
                listeners = int(root.find(".//stats/listeners").text) if root.find(".//stats/listeners") is not None else 0
                artist_cache[artist_name] = (genres, listeners)
                print(f"[DataEDA] Artist: {artist_name} | Genres: {genres} | Playcount: {listeners}")
                return genres, listeners
            except Exception:
                time.sleep(backoff * (attempt + 1))
        artist_cache[artist_name] = ([], 0)
        return [], 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(fetch_artist_info, unique_artists))

    for f, df in dfs.items():
        df["genres"] = df["artist"].map(lambda a: artist_cache.get(a, ([], 0))[0])
        df["playcount"] = df["artist"].map(lambda a: artist_cache.get(a, ([], 0))[1])
        out_path = os.path.join(datasets_dir, f)
        df.to_csv(out_path, index=False)
        print(f"[DataEDA] Saved enriched {f} ({len(df)} rows)")


def enrich_top_recent_with_similar_songs(lastfm_api_key, max_workers=8):

    user_id = session.get("user_info").get("id")
    datasets_dir = os.path.join("temp", user_id, "datasets")
    csv_files = ["top_tracks.csv", "recent_tracks.csv"]
    artist_song_cache = {}

    def fetch_similar_songs(artist_name, track_name):
        key = f"{artist_name}::{track_name}"
        if key in artist_song_cache:
            return artist_song_cache[key]

        similar = []
        try:
            url = f"http://ws.audioscrobbler.com/2.0/?method=track.getsimilar&artist={artist_name}&track={track_name}&api_key={lastfm_api_key}&format=json&limit=3"
            res = requests.get(url, timeout=10)
            res.raise_for_status()
            tracks = res.json().get("similartracks", {}).get("track", [])[:3]
            similar = [{t.get("name", "Unknown"): t.get("artist", {}).get("name", "Unknown")} for t in tracks]
        except Exception as e:
            print(f"[DataEDA] Failed to fetch similar songs for {track_name} by {artist_name}: {e}")

        artist_song_cache[key] = similar
        print(f"[DataEDA] Track: {track_name} by {artist_name} | Similar Songs: {similar}")
        return similar

    for csv_file in csv_files:
        path = os.path.join(datasets_dir, csv_file)
        if not os.path.exists(path):
            print(f"[DataEDA] CSV not found: {path}, skipping")
            continue

        df = pd.read_csv(path)
        if df.empty:
            print(f"[DataEDA] {csv_file} is empty, skipping")
            continue

        df["similar_songs"] = [[] for _ in range(len(df))]

        tasks = [(i, row["artist"], row["name"]) for i, row in df.iterrows() if row.get("artist") and row.get("name")]

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {executor.submit(fetch_similar_songs, artist, track): i for i, artist, track in tasks}
            for future in as_completed(future_to_index):
                i = future_to_index[future]
                try:
                    df.at[i, "similar_songs"] = future.result()
                except Exception:
                    df.at[i, "similar_songs"] = []

        df.to_csv(path, index=False)
        print(f"[DataEDA] Enriched similar songs via Last.fm in {csv_file} ({len(df)} rows)")