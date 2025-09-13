import secrets
import hashlib
import base64
import requests
import shutil
import os
import traceback
from flask import Blueprint, redirect, request, session
from .fetch import (fetch_and_save_user_tracks,
                    fetch_and_save_top_tracks,
                    fetch_and_save_recent_tracks,
                    fetch_and_save_user_details,
                    enrich_user_songs_with_lastfm,
                    enrich_top_recent_with_similar_songs)
from utils.plotting import generate_all_user_plots

SPOTIPY_CLIENT_ID = os.environ.get("SPOTIPY_CLIENT_ID")
REDIRECT_URI = os.environ.get("REDIRECT_URI")
LASTFM_API_KEY = os.environ.get("LASTFM_API_KEY")
SCOPES = "user-read-private user-read-email user-top-read user-read-recently-played"

auth_bp = Blueprint('auth', __name__)
TOKEN_CACHE_DIR = "temp"
os.makedirs(TOKEN_CACHE_DIR, exist_ok=True)

def generate_code_verifier():
    return secrets.token_urlsafe(64)

def generate_code_challenge(verifier):
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b'=').decode('utf-8')

def build_auth_url(code_challenge):
    params = {
        "client_id": SPOTIPY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "code_challenge_method": "S256",
        "code_challenge": code_challenge
    }
    req = requests.Request('GET', "https://accounts.spotify.com/authorize", params=params).prepare()
    return req.url

def exchange_code_for_token(code: str, code_verifier: str) -> str:
    response = requests.post(
        "https://accounts.spotify.com/api/token",
        data={
            "client_id": SPOTIPY_CLIENT_ID,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "code_verifier": code_verifier
        }
    )
    response.raise_for_status()
    return response.json().get("access_token")

def fetch_user_id(token):
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get("https://api.spotify.com/v1/me", headers=headers)
    res.raise_for_status()
    data = res.json()
    return data.get("id")

@auth_bp.route("/login")
def login():
    code_verifier = generate_code_verifier()
    session['code_verifier'] = code_verifier
    auth_url = build_auth_url(generate_code_challenge(code_verifier))
    return redirect(auth_url)

@auth_bp.route("/callback")
def callback():
    code = request.args.get("code")
    code_verifier = session.get("code_verifier")

    if not code or not code_verifier:
        return redirect("/")

    try:
        access_token = exchange_code_for_token(code, code_verifier)
        session['access_token'] = access_token
        print(f"[Auth] Access Token obtained")

        user_id = fetch_user_id(access_token)

        session['user_id'] = user_id

        user_dir = os.path.join("temp", user_id)
        os.makedirs(user_dir, exist_ok=True)

        user_details_file = os.path.join(user_dir, "user_details.json")

        if not os.path.exists(user_details_file):
            print(f"[DataEDA] Folder for user {user_id} is new, generating JSON and CSVs")

            total_playlists, total_tracks = fetch_and_save_user_tracks(user_id=user_id,
                                                                       access_token=access_token)

            fetch_and_save_user_details(user_id=user_id, 
                                        access_token=access_token, 
                                        total_playlists=total_playlists, 
                                        total_tracks=total_tracks)

            fetch_and_save_top_tracks(user_id=user_id, 
                                      access_token=access_token, 
                                      limit=50)

            fetch_and_save_recent_tracks(user_id=user_id, 
                                         access_token=access_token, 
                                         limit=50)

            enrich_user_songs_with_lastfm(user_id=user_id, 
                                          lastfm_api_key=LASTFM_API_KEY)

            enrich_top_recent_with_similar_songs(user_id=user_id, 
                                                 lastfm_api_key=LASTFM_API_KEY)
            print(f"[DataEDA] Created JSON and CSV files for user {user_id}")
            
            generate_all_user_plots(user_id)
        else:
            print(f"[DataEDA] Folder for user {user_id} already exists, skipping JSON and CSV generation")

    except Exception as e:
        print(f"[Auth] Spotify authentication failed: {e}")
        traceback.print_exc()
        return f"Spotify authentication failed: {e}", 500

    return redirect("/")

@auth_bp.route("/logout")
def logout():
    user_id = session.get("user_id")
    if user_id:
        user_dir = os.path.join("temp", user_id)
        if os.path.exists(user_dir) and os.path.isdir(user_dir):
            try:
                shutil.rmtree(user_dir)
                print(f"[Auth] Deleted user folder: {user_dir}")
            except Exception as e:
                print(f"[Auth] Failed to delete user folder: {e}")
    session.clear()
    return redirect("/")