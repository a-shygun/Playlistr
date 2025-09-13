import pycountry
import json
import csv
import os
import pandas as pd
import requests
from xml.etree import ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

def fetch_and_save_user_tracks(user_id, access_token, max_tracks_per_playlist=None):
    headers = {"Authorization": f"Bearer {access_token}"}
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
    print(f"[DataEDA] Found {total_playlists} playlists with a total of {total_playlist_tracks} tracks for user")

    def fetch_playlist_tracks_with_retry(pl, MAX_RETRIES=2, RETRY_DELAY=1):
        pl_name = pl.get("name", "Unnamed Playlist")
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return fetch_playlist_tracks(pl)
            except requests.exceptions.RequestException as e:
                print(f"[DataEDA] Error fetching playlist '{pl_name}' (attempt {attempt}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)
                else:
                    print(f"[DataEDA] Giving up on playlist '{pl_name}' after {MAX_RETRIES} attempts")
                    return []

    def fetch_playlist_tracks(pl):
        pl_id = pl["id"]
        pl_name = pl.get("name", "Unnamed Playlist")
        url = f"https://api.spotify.com/v1/playlists/{pl_id}/tracks?limit=100"
        tracks = []

        while url and (max_tracks_per_playlist is None or len(tracks) < max_tracks_per_playlist):
            res = requests.get(url, headers=headers)
            res.raise_for_status()
            data = res.json()

            for item in data.get("items", []):
                t = item.get("track")
                if not t:
                    continue
                artist_name = t["artists"][0]["name"] if t.get("artists") else ""
                release_date = t.get("album", {}).get("release_date", "1900")
                year = int(release_date[:4]) if release_date else 1900

                track_info = {
                    "playlist": pl_name,
                    "name": t.get("name"),
                    "name_url": t.get("external_urls", {}).get("spotify", ""),
                    "artist": artist_name,
                    "artist_url": t.get("artists")[0].get("external_urls", {}).get("spotify", "") if t.get("artists") else "",
                    "album": t.get("album", {}).get("name", ""),
                    "album_url": t.get("album", {}).get("external_urls", {}).get("spotify", ""),
                    "year": year,
                    "album_art": t.get("album", {}).get("images", [{}])[0].get("url", ""),
                    "genres": ""
                }
                tracks.append(track_info)

                if max_tracks_per_playlist is not None and len(tracks) >= max_tracks_per_playlist:
                    break

            url = data.get("next") if max_tracks_per_playlist is None or len(tracks) < max_tracks_per_playlist else None

        print(f"[DataEDA] {pl_name}: collected {len(tracks)} tracks (fetched limit)")
        return tracks

    all_tracks = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_playlist_tracks_with_retry, pl): pl for pl in playlists}
        for f in as_completed(futures):
            pl_name = futures[f].get("name", "Unnamed Playlist")
            try:
                all_tracks.extend(f.result())
            except Exception as e:
                print(f"[DataEDA] Unexpected error fetching playlist '{pl_name}': {e}")

    print(f"[DataEDA] Total collected tracks (fetched limit): {len(all_tracks)}")

    user_dir = os.path.join("temp", user_id)
    os.makedirs(user_dir, exist_ok=True)
    csv_file = os.path.join(user_dir, "user_songs.csv")
    fieldnames = ["playlist", "name", "name_url", "artist", "artist_url",
                  "album", "album_url", "year", "album_art", "genres"]

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for t in all_tracks:
            writer.writerow({k: t.get(k, "") for k in fieldnames})

    print(f"[DataEDA] Saved {len(all_tracks)} tracks to {csv_file}")
    return total_playlists, total_playlist_tracks

def fetch_and_save_top_tracks(user_id, access_token, limit=50):
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"https://api.spotify.com/v1/me/top/tracks?limit={limit}"

    res = requests.get(url, headers=headers)
    res.raise_for_status()
    data = res.json()

    tracks = []
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
        tracks.append(track_info)

    user_dir = os.path.join("temp", str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    csv_file = os.path.join(user_dir, "top_tracks.csv")

    fieldnames = ["playlist", "name", "name_url", "artist", "artist_url",
                  "album", "album_url", "year", "album_art", "genres"]

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for t in tracks:
            row = {k: t.get(k, "") for k in fieldnames}
            writer.writerow(row)

    print(f"[DataEDA] Saved {len(tracks)} top tracks to {csv_file}")

def fetch_and_save_recent_tracks(user_id, access_token, limit=50):
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"https://api.spotify.com/v1/me/player/recently-played?limit={limit}"

    res = requests.get(url, headers=headers)
    res.raise_for_status()
    data = res.json()

    tracks = []
    for item in data.get("items", []):
        t = item.get("track")
        if not t:
            continue
        artist_name = t["artists"][0]["name"] if t.get("artists") else ""
        release_date = t.get("album", {}).get("release_date", "1900")
        year = int(release_date[:4]) if release_date else 1900

        track_info = {
            "playlist": "Recent Tracks",
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
        tracks.append(track_info)

    user_dir = os.path.join("temp", str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    csv_file = os.path.join(user_dir, "recent_tracks.csv")

    fieldnames = ["playlist", "name", "name_url", "artist", "artist_url",
                  "album", "album_url", "year", "album_art", "genres"]

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for t in tracks:
            row = {k: t.get(k, "") for k in fieldnames}
            writer.writerow(row)

    print(f"[DataEDA] Saved {len(tracks)} recent tracks to {csv_file}")

def fetch_and_save_user_details(user_id, access_token, total_playlists, total_tracks):

    headers = {"Authorization": f"Bearer {access_token}"}
    url = "https://api.spotify.com/v1/me"

    try:
        res = requests.get(url, headers=headers, timeout=30)
        res.raise_for_status()
        data = res.json()

        country_code = data.get("country")
        country_name = pycountry.countries.get(alpha_2=country_code).name if country_code else None

        user_details = {
            "name": data.get("display_name"),
            "email": data.get("email"),
            "img": data.get("images", [{}])[0].get("url", ""),
            "country": country_name,
            "product": data.get("product"),
            "spotify_link": data.get("external_urls", {}).get("spotify", ""),
            "total_playlists": total_playlists,
            "total_playlist_tracks":  total_tracks,
            "id": data.get("id")
        }

        user_dir = os.path.join("temp", user_id)
        os.makedirs(user_dir, exist_ok=True)

        json_file = os.path.join(user_dir, "user_details.json")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(user_details, f, indent=4)

        print(f"[DataEDA] Saved user details JSON at {json_file}")
        return user_details

    except Exception as e:
        print(f"[DataEDA] Failed to fetch user details: {e}")
        raise






def enrich_user_songs_with_lastfm(user_id, lastfm_api_key, max_workers=8, retry_count=3, backoff=2):
    user_dir = os.path.join("temp", user_id)
    os.makedirs(user_dir, exist_ok=True)
    csv_files = ["user_songs.csv", "top_tracks.csv", "recent_tracks.csv"]

    dfs = []
    for f_name in csv_files:
        path = os.path.join(user_dir, f_name)
        if os.path.exists(path):
            print(f"[DataEDA] Reading {path}")
            dfs.append(pd.read_csv(path))
        else:
            print(f"[DataEDA] CSV not found: {path}, skipping")
    if not dfs:
        print("[DataEDA] No CSVs found. Exiting.")
        return

    df = pd.concat(dfs, ignore_index=True)
    initial_len = len(df)
    df.drop_duplicates(subset=["name", "artist"], inplace=True)
    print(f"[DataEDA] Dropped {initial_len - len(df)} duplicates, {len(df)} rows remain")

    unique_artists = df["artist"].dropna().unique()
    artist_cache = {}
    def get_with_retries(url):
        for attempt in range(1, retry_count + 1):
            try:
                res = requests.get(url, timeout=10)
                res.raise_for_status()
                return res.text
            except Exception as e:
                print(f"[Retry] Attempt {attempt} failed for URL: {url} | {e}")
                time.sleep(backoff * attempt)
        print(f"[DataEDA] Failed to fetch after {retry_count} retries: {url}")
        return None

    def fetch_artist_info(artist_name):
        if artist_name in artist_cache:
            return artist_cache[artist_name]

        url = f"http://ws.audioscrobbler.com/2.0/?method=artist.getInfo&artist={artist_name}&api_key={lastfm_api_key}&format=xml"
        xml_text = get_with_retries(url)
        genres, listeners = [], 0

        if xml_text:
            try:
                root = ET.fromstring(xml_text)
                tags_root = root.find(".//tags")
                if tags_root is not None:
                    genres = [t.find("name").text for t in tags_root.findall("tag")][:3]

                stats = root.find(".//stats")
                if stats is not None and stats.find("listeners") is not None:
                    listeners = int(stats.find("listeners").text)
            except Exception as e:
                print(f"[DataEDA] Failed parsing XML for {artist_name}: {e}")

        artist_cache[artist_name] = (genres, listeners)
        return genres, listeners

    print(f"[DataEDA] Fetching info for {len(unique_artists)} unique artists...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_artist = {executor.submit(fetch_artist_info, artist): artist for artist in unique_artists}
        for future in as_completed(future_to_artist):
            artist = future_to_artist[future]
            try:
                genres, listeners = future.result()
                print(f"[DataEDA] Fetched: {artist} | genres: {genres} | listeners: {listeners}")
            except Exception as e:
                print(f"[DataEDA] Error fetching {artist}: {e}")

    df["genres"] = df["artist"].map(lambda a: artist_cache.get(a, ([], 0))[0])
    df["playcount"] = df["artist"].map(lambda a: artist_cache.get(a, ([], 0))[1])

    out_path = os.path.join(user_dir, "user_songs.csv")
    df.to_csv(out_path, index=False)
    print(f"[DataEDA] Saved enriched CSV to {out_path} ({len(df)} rows)")
    


def enrich_top_recent_with_similar_songs(user_id, lastfm_api_key):

    user_dir = os.path.join("temp", user_id)
    csv_files = ["top_tracks.csv", "recent_tracks.csv"]
    artist_song_cache = {}
    def fetch_similar_songs(artist_name, track_name):
        cache_key = f"{artist_name}::{track_name}"
        if cache_key in artist_song_cache:
            return artist_song_cache[cache_key]

        similar = []
        try:
            url = (
                f"http://ws.audioscrobbler.com/2.0/?method=track.getsimilar"
                f"&artist={artist_name}&track={track_name}&api_key={lastfm_api_key}&format=json&limit=3"
            )
            res = requests.get(url, timeout=10)
            data = res.json()
            tracks = data.get("similartracks", {}).get("track", [])
            for t in tracks[:3]:
                similar.append({t.get("name", "Unknown"): t.get("artist", {}).get("name", "Unknown")})
        except Exception as e:
            print(f"[DataEDA] Failed to fetch similar songs for {track_name} by {artist_name}: {e}")

        artist_song_cache[cache_key] = similar
        return similar

    for csv_file_name in csv_files:
        csv_path = os.path.join(user_dir, csv_file_name)
        if not os.path.exists(csv_path):
            print(f"[DataEDA] CSV not found: {csv_path}, skipping")
            continue

        with open(csv_path, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {
                executor.submit(fetch_similar_songs, row.get("artist", ""), row.get("name", "")): row
                for row in rows
                if row.get("artist") and row.get("name")
            }

            for f in as_completed(futures):
                row = futures[f]
                try:
                    row["similar_songs"] = f.result()
                except Exception:
                    row["similar_songs"] = []

        fieldnames = list(rows[0].keys()) if rows else [
            "playlist", "name", "name_url", "artist", "artist_url",
            "album", "album_url", "year", "album_art",
            "genres", "similar_songs"
        ]
        if "similar_songs" not in fieldnames:
            fieldnames.append("similar_songs")

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

        print(f"[DataEDA] Enriched similar songs via Last.fm in {csv_file_name} ({len(rows)} rows)")
