
from flask import Blueprint, session, render_template
import os, json, requests
from time import time
import pycountry
from .spotify_lastfm import fetch_tracks_with_genres_and_similar

views_bp = Blueprint('views', __name__)
CACHE_DIR = "temp"
CACHE_TTL = 3600

LASTFM_API_KEY = os.environ.get("LASTFM_API_KEY")
if not LASTFM_API_KEY:
    raise ValueError("LASTFM_API_KEY not found in env")

os.makedirs(CACHE_DIR, exist_ok=True)

def get_cache_file(user_id):
    return os.path.join(CACHE_DIR, f"user_cache_{user_id}.json")

def load_cache(user_id):
    path = get_cache_file(user_id)
    if os.path.exists(path):
        with open(path, "r") as f:
            try:
                data = json.load(f)
                if time() - data.get("timestamp", 0) < CACHE_TTL:
                    return data
            except json.JSONDecodeError:
                pass
    return None

def save_cache(user_id, user_data, top_tracks, recent_tracks, token=None):
    path = get_cache_file(user_id)
    cache_data = {
        "timestamp": time(),
        "user": user_data,
        "top_tracks": top_tracks,
        "recent_tracks": recent_tracks
    }
    if token:
        cache_data["access_token"] = token
    with open(path, "w") as f:
        json.dump(cache_data, f)

def delete_cache(user_id):
    path = get_cache_file(user_id)
    if os.path.exists(path):
        os.remove(path)

def get_user_info(token):
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get("https://api.spotify.com/v1/me", headers=headers)
    if res.status_code != 200:
        return None

    data = res.json()
    total_playlists, total_playlist_tracks = 0, 0
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

    return {
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

def ensure_cache(user_id, token):
    cached = load_cache(user_id)
    if cached:
        return cached["top_tracks"], cached["recent_tracks"], cached["user"], cached.get("access_token")
    user_data = get_user_info(token)
    if not user_data:
        return [], [], None, None
    top_tracks, recent_tracks = fetch_tracks_with_genres_and_similar(token, limit=50, lastfm_api_key=LASTFM_API_KEY)
    save_cache(user_id, user_data, top_tracks, recent_tracks, token)
    return top_tracks, recent_tracks, user_data, token

# Routes
@views_bp.route("/")
def dashboard():
    token = session.get("access_token")
    if not token:
        return render_template("base.html", user=None, default_page="home")
    user_id = session.get("user_id")
    top_tracks, recent_tracks, user, _ = ensure_cache(user_id, token)
    if not user:
        session.clear()
        return render_template("base.html", user=None, default_page="home")
    return render_template("base.html", user=user, default_page="tracks", top_tracks=top_tracks, recent_tracks=recent_tracks)

@views_bp.route("/tracks")
def tracks():
    token = session.get("access_token")
    if not token:
        return render_template("blocks/tracks.html", user=None, top_tracks=[], recent_tracks=[])
    user_id = session.get("user_id")
    top_tracks, recent_tracks, user, _ = ensure_cache(user_id, token)
    if not user:
        session.clear()
        return render_template("blocks/tracks.html", user=None, top_tracks=[], recent_tracks=[])
    return render_template("blocks/tracks.html", user=user, top_tracks=top_tracks, recent_tracks=recent_tracks)

@views_bp.route("/home")
def home_fragment():
    token = session.get("access_token")
    user_id = session.get("user_id")
    user = None
    if token:
        _, _, user, _ = ensure_cache(user_id, token)
    return render_template("blocks/home.html", user=user)

@views_bp.route("/block3")
def block3():
    return render_template("blocks/block3.html")

@views_bp.route("/profile")
def profile():
    token = session.get("access_token")
    if not token:
        return render_template("blocks/profile.html", user=None)
    user_id = session.get("user_id")
    _, _, user, _ = ensure_cache(user_id, token)
    if not user:
        session.clear()
        return render_template("blocks/profile.html", user=None)
    return render_template("blocks/profile.html", user=user)

@views_bp.route("/logout")
def logout():
    user_id = session.get("user_id")
    if user_id:
        delete_cache(user_id)
    session.clear()
    return render_template("base.html", user=None, default_page="home")

