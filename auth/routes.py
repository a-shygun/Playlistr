
import os
import json
import secrets
import hashlib
import base64
import requests
from flask import Blueprint, session, redirect, request

SPOTIPY_CLIENT_ID = os.environ.get("SPOTIPY_CLIENT_ID")
REDIRECT_URI = os.environ.get("REDIRECT_URI")
# REDIRECT_URI = "http://127.0.0.1:5000/callback"
SCOPES = "user-read-private user-read-email user-top-read user-read-recently-played"

auth_bp = Blueprint('auth', __name__)
TOKEN_CACHE_DIR = "temp"
os.makedirs(TOKEN_CACHE_DIR, exist_ok=True)

def get_token_cache_file(user_id):
    return os.path.join(TOKEN_CACHE_DIR, f".spotify_token_cache_{user_id}.json")

def generate_code_verifier():
    verifier = secrets.token_urlsafe(64)
    print(f"[PKCE] Generated code verifier: {verifier}")
    return verifier

def generate_code_challenge(verifier):
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b'=').decode('utf-8')
    print(f"[PKCE] Generated code challenge: {challenge}")
    return challenge

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
    print(f"[Spotify OAuth] Built auth URL: {req.url}")
    return req.url

def exchange_code_for_token(code: str, code_verifier: str) -> str:
    print("[Spotify OAuth] Exchanging code for token")
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
    token = response.json().get("access_token")
    print(f"[Spotify OAuth] Access token received: {token}")
    return token

@auth_bp.route("/login")
def login():
    code_verifier = generate_code_verifier()
    session['code_verifier'] = code_verifier
    code_challenge = generate_code_challenge(code_verifier)
    auth_url = build_auth_url(code_challenge)
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
        res = requests.get(
            "https://api.spotify.com/v1/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if res.status_code != 200:
            return f"Failed to fetch user info: {res.text}", res.status_code
        user_info = res.json()
        user_id = user_info.get("id")
        if not user_id:
            raise ValueError("Could not retrieve user ID from Spotify")
        session['user_id'] = user_id
        token_file = get_token_cache_file(user_id)
        with open(token_file, "w") as f:
            json.dump({"access_token": access_token}, f)
    except Exception as e:
        return f"Failed to get access token: {e}", 500
    return redirect("/")
@auth_bp.route("/logout")
def logout():
    user_id = session.get("user_id")
    if user_id:
        token_file = get_token_cache_file(user_id)
        if os.path.exists(token_file):
            os.remove(token_file)
    session.clear()
    return redirect("/")