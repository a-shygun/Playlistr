import secrets
import hashlib
import base64
import requests
import shutil
import os
import traceback
import json
from flask import Blueprint, redirect, request, session, render_template
from utils.plotting import generate_all_user_plots 
from .fetch import (fetch_user_info,
                    fetch_save_user_tracks,
                    save_user_info,
                    fetch_save_top_tracks,
                    fetch_save_recent_tracks,
                    enrich_songs_with_lastfm,
                    enrich_top_recent_with_similar_songs)

SPOTIPY_CLIENT_ID = os.environ.get("SPOTIPY_CLIENT_ID")
REDIRECT_URI = os.environ.get("REDIRECT_URI")
LASTFM_API_KEY = os.environ.get("LASTFM_API_KEY")
SCOPES = "user-read-private user-read-email user-top-read user-read-recently-played"

auth_bp = Blueprint('auth', __name__)

def build_auth_url_with_challenge():
    code_verifier = secrets.token_urlsafe(64)
    session['code_verifier'] = code_verifier
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b'=').decode('utf-8')
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

@auth_bp.route("/login")
def login():
    auth_url = build_auth_url_with_challenge()
    return redirect(auth_url)

def set_access_token():
    code = request.args.get("code")
    code_verifier = session.get("code_verifier")

    token_res = requests.post(
        "https://accounts.spotify.com/api/token",
        data={
            "client_id": SPOTIPY_CLIENT_ID,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "code_verifier": code_verifier,
        },
    )
    token_res.raise_for_status()
    access_token = token_res.json().get("access_token")
    session['access_token'] = access_token


@auth_bp.route("/logout")
def logout():
    user_info = session.get('user_info')
    user_id = user_info.get("user_id")
    if user_id:
        try:
            user_dir = os.path.join("temp", user_id)
            shutil.rmtree(user_dir)
            print(f"[Auth] Deleted user folder: {user_dir}")
        except Exception as e:
            print(f"[Auth] Failed to delete user folder: {e}")
    session.clear()
    return redirect("/")

@auth_bp.route("/callback")
def callback():
    try:
        set_access_token()
        fetch_user_info()
    except Exception as e:
        traceback.print_exc()
        return f"Spotify authentication failed: {e}", 500

    return render_template("loading.html")

@auth_bp.route("/setup")
def setup():
    try:
        user_info = session.get("user_info")
        user_id = user_info.get("id")
        user_dir = os.path.join("temp", user_id)
        datasets_dir = os.path.join(user_dir, "datasets")
        plots_dir = os.path.join(user_dir, "plots")

        os.makedirs(datasets_dir, exist_ok=True)
        os.makedirs(plots_dir, exist_ok=True)

        if not os.listdir(datasets_dir):
            print(f"[DataEDA] Datasets folder empty for user {user_id}, generating CSVs and JSON")
            fetch_save_user_tracks()
            save_user_info()
            fetch_save_top_tracks()
            fetch_save_recent_tracks()
            enrich_songs_with_lastfm(lastfm_api_key=LASTFM_API_KEY)
            enrich_top_recent_with_similar_songs(lastfm_api_key=LASTFM_API_KEY)
            print(f"[DataEDA] Datasets created for user {user_id}")
        else:
            print(f"[DataEDA] Datasets already exist for user {user_id}, skipping generation")

        if not os.listdir(plots_dir):
            print(f"[DataEDA] Plots folder empty for user {user_id}, generating plots")
            generate_all_user_plots()
            print(f"[DataEDA] Plots created for user {user_id}")
        else:
            print(f"[DataEDA] Plots already exist for user {user_id}, skipping generation")

        user_info_file = os.path.join(datasets_dir, "user_info.json")
        if os.path.exists(user_info_file):
            with open(user_info_file, "r") as f:
                session["user_info"] = json.load(f)

    except Exception as e:
        print(f"[Setup] Error during setup: {e}")
        traceback.print_exc()
        return f"Setup failed: {e}", 500

    return redirect("/")