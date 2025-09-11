import secrets
import hashlib
import base64
import requests
import os
import json
from flask import Blueprint, session, redirect, request

# SPOTIPY_CLIENT_ID = "35d3c6267f8249bb97d537ce1b40b0a8"
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")

REDIRECT_URI = "http://127.0.0.1:5000/callback"
SCOPES = "user-read-private user-read-email user-top-read user-read-recently-played"

TOKEN_CACHE = "temp/.spotify_token_cache.json"
auth_bp = Blueprint('auth', __name__)


def generate_code_verifier():
    verifier = secrets.token_urlsafe(64)
    print(f"[PKCE] Generated code verifier: {verifier}")
    return verifier


def generate_code_challenge(verifier):
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b'=').decode('utf-8')
    print(f"[PKCE] Generated code challenge from verifier: {challenge}")
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
    print(f"[Spotify OAuth] Built authorization URL: {req.url}")
    return req.url


def exchange_code_for_token(code: str, code_verifier: str) -> str:
    """Exchange authorization code for access token."""
    print(f"[Spotify OAuth] Exchanging code for token. Code: {code}, Verifier: {code_verifier}")
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
    print(f"[Spotify OAuth] Token response status: {response.status_code}")
    response.raise_for_status()
    access_token = response.json().get('access_token')
    print(f"[Spotify OAuth] Access token received: {access_token}")
    return access_token



@auth_bp.route("/login")
def login():
    print("[Route] /login called")
    if os.path.exists(TOKEN_CACHE):
        with open(TOKEN_CACHE, "r") as f:
            data = json.load(f)
            session['access_token'] = data.get("access_token")
            print(f"[Route] Loaded access token from cache: {session['access_token']}")
        return redirect("/")

    code_verifier = generate_code_verifier()
    session['code_verifier'] = code_verifier
    code_challenge = generate_code_challenge(code_verifier)
    auth_url = build_auth_url(code_challenge)
    print(f"[Route] Redirecting user to Spotify auth URL")
    return redirect(auth_url)


@auth_bp.route("/callback")
def callback():
    print("[Route] /callback called")
    code = request.args.get('code')
    code_verifier = session.get('code_verifier')
    print(f"[Route] Received code: {code}")
    print(f"[Route] Using code_verifier from session: {code_verifier}")

    if not code:
        print("[Route] No code received, redirecting to /")
        return redirect("/")

    try:
        access_token = exchange_code_for_token(code, code_verifier)
        session['access_token'] = access_token
        print(f"[Route] Stored access token in session")

        with open(TOKEN_CACHE, "w") as f:
            json.dump({"access_token": access_token}, f)
            print(f"[Route] Saved access token to cache file: {TOKEN_CACHE}")

    except Exception as e:
        print(f"[Route] Failed to get access token: {e}")
        return f"Failed to get access token: {e}", 500

    return redirect("/")