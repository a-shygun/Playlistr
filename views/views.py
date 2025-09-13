from flask import Blueprint, session, render_template, jsonify, request, send_from_directory
import os, ssl, smtplib
import os
import csv 
import json 
import ast
import pandas as pd

def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def read_tracks_csv(path):
    if not os.path.exists(path):
        return []
    df = pd.read_csv(path)
    for col in ["genres", "similar_songs"]:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: ast.literal_eval(x) if pd.notna(x) else [])
    return df.to_dict(orient="records")

views_bp = Blueprint('views', __name__)

@views_bp.route("/")
def dashboard():
    user_id = session.get("user_id")
    if not user_id:
        return render_template("base.html", user=None, default_page="home")
    user_dir = os.path.join("temp", user_id)
    top_tracks = read_csv(os.path.join(user_dir, "top_tracks.csv"))
    recent_tracks = read_csv(os.path.join(user_dir, "recent_tracks.csv"))
    user = read_json(os.path.join(user_dir, "user_details.json"))
    return render_template(
        "base.html",
        user=user,
        default_page="tracks",
        top_tracks=top_tracks,
        recent_tracks=recent_tracks
    )

@views_bp.route("/tracks")
def tracks():
    user_id = session.get("user_id")
    if not user_id:
        return render_template("blocks/tracks.html", user=None, top_tracks=[], recent_tracks=[])
    user_dir = os.path.join("temp", user_id)
    top_tracks = read_tracks_csv(os.path.join(user_dir, "top_tracks.csv"))
    recent_tracks = read_tracks_csv(os.path.join(user_dir, "recent_tracks.csv"))
    user = read_json(os.path.join(user_dir, "user_details.json"))

    return render_template("blocks/tracks.html", user=user, top_tracks=top_tracks, recent_tracks=recent_tracks)

@views_bp.route("/home")
def home_fragment():
    user_id = session.get("user_id")
    user = read_json(os.path.join("temp", user_id, "user_details.json")) if user_id else None
    return render_template("blocks/home.html", user=user)

@views_bp.route("/profile")
def profile():
    user_id = session.get("user_id")
    user = read_json(os.path.join("temp", user_id, "user_details.json")) if user_id else None
    return render_template("blocks/profile.html", user=user)


from utils.plotting import load_user_data, get_artist_genre_playlist_network_html

@views_bp.route("/data")
def data():
    user_id = session.get("user_id")
    if not user_id:
        return render_template("blocks/data.html", user=None, plots=[], network_html=None)

    user_dir = os.path.join("temp", user_id, "plots")
    plots = [fname for fname in os.listdir(user_dir) if fname.endswith(".png")] if os.path.exists(user_dir) else []
    plots.sort()

    df = load_user_data(user_id)
    network_html = get_artist_genre_playlist_network_html(df)  # HTML string

    user = read_json(os.path.join("temp", user_id, "user_details.json"))

    return render_template(
        "blocks/data.html",
        user=user,
        plots=plots,
        network_html=network_html
    )
    
@views_bp.route("/network")
def network():
    df = load_user_data(session['user_id'])
    net_html = get_artist_genre_playlist_network_html(df)
    return net_html

@views_bp.route("/user_plots/<user_id>/<filename>")
def user_plots(user_id, filename):
    return send_from_directory(os.path.join("temp", user_id, "plots"), filename)

@views_bp.route("/register", methods=["POST"])
def register():
    data = request.json
    email = data.get("email")
    username = data.get("username")
    if not email or not username:
        return jsonify({"message": "Email and Username are required"}), 400

    sender = "ryxnole@gmail.com"
    receiver = "ryan.shygun@gmail.com"
    password = os.getenv("GMAIL_APP_PASSWORD")
    subject = "New Spotify Dashboard Registration Request"
    body = f"New registration request:\n\nSpotify Email: {email}\nUsername: {username}"
    message = f"Subject: {subject}\n\n{body}"

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender, password)
            server.sendmail(sender, receiver, message)
        return jsonify({"message": "Your request has been sent! Please wait for approval."})
    except Exception as e:
        return jsonify({"message": f"Failed to send email: {str(e)}"}), 500