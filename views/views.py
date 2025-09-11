from flask import Blueprint, session, render_template
import os, json
from time import time
from dotenv import load_dotenv
import requests
from .spotify_lastfm import fetch_tracks_with_genres_and_similar
import pycountry


views_bp = Blueprint('views', __name__)
CACHE_FILE = "temp/profile_cache.json"
CACHE_TTL = 90000


# load_dotenv(".venv/secure/tokens.env")
# LASTFM_API_KEY = os.getenv("LASTFM_API_KEY"
LASTFM_API_KEY = os.environ.get("LASTFM_API_KEY")

if not LASTFM_API_KEY:
    raise ValueError("LASTFM_API_KEY not found in env")
print(f"[Env] LASTFM_API_KEY loaded: {'Yes' if LASTFM_API_KEY else 'No'}")


def load_cache():
    print("[Cache] Attempting to load cache")
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            try:
                data = json.load(f)
                if time() - data.get("timestamp", 0) < CACHE_TTL:
                    print("[Cache] Cache hit")
                    return data
                else:
                    print("[Cache] Cache expired")
            except json.JSONDecodeError:
                print("[Cache] Cache file is corrupted")
    else:
        print("[Cache] No cache file found")
    return None

def save_cache(user, top_tracks, recent_tracks):
    print("[Cache] Saving cache")
    with open(CACHE_FILE, "w") as f:
        json.dump({
            "timestamp": time(),
            "user": user,
            "top_tracks": top_tracks,
            "recent_tracks": recent_tracks
        }, f)
    print("[Cache] Cache saved successfully")


def get_user_info(token):
    print("[Spotify] Fetching user info from Spotify API")

    headers = {"Authorization": f"Bearer {token}"}

    
    res = requests.get("https://api.spotify.com/v1/me", headers=headers)
    if res.status_code != 200:
        print(f"[Spotify] Failed to fetch user info, status={res.status_code}")
        return None
    data = res.json()

    
    total_playlists = 0
    total_playlist_tracks = 0
    next_url = "https://api.spotify.com/v1/me/playlists?limit=50"

    while next_url:
        playlists_res = requests.get(next_url, headers=headers)
        if playlists_res.status_code != 200:
            break
        playlists_data = playlists_res.json()

        total_playlists = playlists_data.get("total", 0)
        for pl in playlists_data.get("items", []):
            total_playlist_tracks += pl["tracks"]["total"]

        next_url = playlists_data.get("next")  

    
    liked_res = requests.get("https://api.spotify.com/v1/me/tracks?limit=1", headers=headers)
    liked_total = liked_res.json().get("total", 0) if liked_res.status_code == 200 else 0

    
    country_code = data.get("country")
    country_name = pycountry.countries.get(alpha_2=country_code).name if country_code else None

    
    user_info = {
        "name": data.get("display_name"),
        "email": data.get("email"),
        "img": data.get("images")[0]["url"] if data.get("images") else None,
        "country": country_name,
        "product": data.get("product"),  
        "followers": data.get("followers", {}).get("total", 0),
        "spotify_link": data.get("external_urls", {}).get("spotify"),
        "total_playlists": total_playlists,
        "total_playlist_tracks": total_playlist_tracks,
        "liked_songs": liked_total,
        "id": data.get("id"),
    }

    print(f"[Spotify] User info fetched: {user_info}")
    return user_info


@views_bp.route("/")
def dashboard():
    print("[Route] /dashboard called")
    token = session.get("access_token")
    if not token:
        print("[Route] No access token in session, rendering base.html with no user")
        return render_template("base.html", user=None, default_page="home")

    cached = load_cache()
    if cached:
        print("[Route] Using cached data for dashboard")
        user = cached["user"]
        top_tracks = cached["top_tracks"]
        recent_tracks = cached["recent_tracks"]
    else:
        print("[Route] No valid cache found, fetching data from APIs")
        user = get_user_info(token)
        top_tracks, recent_tracks = fetch_tracks_with_genres_and_similar(
            token, limit=50, lastfm_api_key=LASTFM_API_KEY
        )
        save_cache(user, top_tracks, recent_tracks)

    return render_template(
        "base.html",
        user=user,
        default_page="tracks",
        top_tracks=top_tracks,
        recent_tracks=recent_tracks
    )

@views_bp.route("/home")
def home_fragment():
    print("[Route] /home called")
    token = session.get("access_token")
    if not token:
        print("[Route] No token, rendering home.html with user=None")
        return render_template("blocks/home.html", user=None)

    cached = load_cache()
    user = cached["user"] if cached else get_user_info(token)
    print(f"[Route] Rendering home.html for user: {user}")
    return render_template("blocks/home.html", user=user)

@views_bp.route("/tracks")
def tracks():
    print("[Route] /tracks called")
    token = session.get("access_token")
    if not token:
        print("[Route] No token, rendering tracks.html with empty lists")
        return render_template(
            "blocks/tracks.html",
            user=None,              
            top_tracks=[],
            recent_tracks=[]
        )

    cached = load_cache()
    if cached:
        print("[Route] Using cached track data")
        top_tracks = cached["top_tracks"]
        recent_tracks = cached["recent_tracks"]
        user = cached["user"]
    else:
        print("[Route] No valid cache, fetching tracks from Spotify and LastFM")
        user = get_user_info(token)
        top_tracks, recent_tracks = fetch_tracks_with_genres_and_similar(
            token, limit=50, lastfm_api_key=LASTFM_API_KEY
        )
        save_cache(user, top_tracks, recent_tracks)

    print(f"[Route] Rendering tracks.html for user {user} with {len(top_tracks)} top tracks and {len(recent_tracks)} recent tracks")
    return render_template(
        "blocks/tracks.html",
        user=user,
        top_tracks=top_tracks,
        recent_tracks=recent_tracks
    )
@views_bp.route("/block3")
def block3():
    print("[Route] /block3 called")
    return render_template("blocks/block3.html")


@views_bp.route("/logout")
def logout():
    print("[Route] /logout called")
    session.clear()
    return render_template("base.html", user=None, default_page="home")

@views_bp.route("/profile")
def profile():
    print("[Route] /profile called")

    token = session.get("access_token")
    if not token:
        print("[Route] No Spotify token found in session")
        return render_template("blocks/profile.html", user=None)

    cached = load_cache()
    if cached and "user" in cached:
        print("[Route] Using cached user profile")
        user = cached["user"]
    else:
        print("[Route] Fetching fresh user profile")
        user = get_user_info(token)
        
        top_tracks = cached["top_tracks"] if cached else []
        recent_tracks = cached["recent_tracks"] if cached else []
        save_cache(user, top_tracks, recent_tracks)

    return render_template("blocks/profile.html", user=user)







































































































































































