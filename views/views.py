from flask import Blueprint, session, render_template, jsonify, request, send_from_directory, send_file
import os, ssl, smtplib
import os
import csv 
import json 
import ast
import pandas as pd
from utils.plotting import load_user_data, get_artist_genre_playlist_network_html

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
    user_info = session.get('user_info')
    return render_template("base.html", user=user_info, content="pages/home.html")

@views_bp.route("/tracks")
def tracks():
    user_info = session.get("user_info")
    top_tracks = recent_tracks = None

    if user_info:
        user_dir = os.path.join("temp", user_info["id"], "datasets")
        top_tracks = read_tracks_csv(os.path.join(user_dir, "top_tracks.csv"))
        recent_tracks = read_tracks_csv(os.path.join(user_dir, "recent_tracks.csv"))

    return render_template(
        "pages/tracks.html",
        user=user_info,
        content="pages/tracks.html",
        top_tracks=top_tracks,
        recent_tracks=recent_tracks
    )
    
@views_bp.route("/home")
def home():
    user_info = session.get('user_info')
    return render_template("pages/home.html", user=user_info)

@views_bp.route("/profile")
def profile():
    user_info = session.get('user_info')
    return render_template("pages/profile.html", user=user_info)

@views_bp.route("/data")
def data():
    user_info = session.get("user_info")
    plot_images = []
    plot_json = None

    if user_info:
        plots_dir = os.path.join("temp", user_info["id"], "plots")
        if os.path.exists(plots_dir):
            plot_images = [fname for fname in os.listdir(plots_dir) if fname.endswith(".png")]
            plot_images.sort()

            json_path = os.path.join(plots_dir, "plot_expo.json")
            if os.path.exists(json_path):
                with open(json_path, "r") as f:
                    plot_json = json.load(f)

    return render_template(
        "pages/data.html",
        user=user_info,
        plots=plot_images,
        plot_json=plot_json
    )
    
@views_bp.route("/user_plot_data")
def user_plot_data():
    user_info = session.get("user_info")
    if not user_info:
        return {}, 403

    plot_file = os.path.join("temp", user_info["id"], "plots", "plot_expo.json")
    if not os.path.exists(plot_file):
        return {}, 404

    with open(plot_file, "r") as f:
        plot_json = json.load(f)
    return plot_json
    
    
@views_bp.route("/network")
def network():
    user_info = session.get('user_info')
    user_id = user_info.get('id')
    df = load_user_data(user_id)
    plots_dir = os.path.join("temp", user_id, "plots")
    net_html = get_artist_genre_playlist_network_html(df, plots_dir)
    return net_html

@views_bp.route("/user_plots/<filename>")
def user_plots(filename):
    user_info = session.get("user_info")

    # Special case: serve placeholder replica if filename matches
    if filename == "plot_json_placeholder.json":
        placeholder_path = os.path.join("static", "img", "placeholder", "plot_json.json")
        if os.path.exists(placeholder_path):
            return send_file(placeholder_path, mimetype="application/json")
        else:
            return "Placeholder file not found", 404

    # Normal user-specific behavior
    if not user_info or not user_info.get("id"):
        return "User not logged in", 403

    user_id = user_info["id"]
    plots_dir = os.path.join("temp", user_id, "plots")

    file_path = os.path.join(plots_dir, filename)
    if not os.path.exists(file_path):
        return "File not found", 404

    return send_from_directory(plots_dir, filename)
@views_bp.route("/register", methods=["POST"])
def register():
    print("[Register] Route hit")

    data = request.json
    print("[Register] Incoming data:", data)

    email = data.get("email")
    username = data.get("username")
    print(f"[Register] Email: {email}, Username: {username}")

    if not email or not username:
        print("[Register] Missing email or username")
        return jsonify({"message": "Email and Username are required"}), 400

    sender = "ryxnole@gmail.com"
    receiver = "ryan.shygun@gmail.com"
    password = os.getenv("GMAIL_APP_PASSWORD")

    if not password:
        print("[Register] ERROR: GMAIL_APP_PASSWORD not found in environment variables")
        return jsonify({"message": "Email server not configured"}), 500

    subject = "New Spotify Dashboard Registration Request"
    body = f"New registration request:\n\nSpotify Email: {email}\nUsername: {username}"
    message = f"Subject: {subject}\n\n{body}"

    print("[Register] Preparing to send email...")

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            print("[Register] Connected to Gmail SMTP")
            server.login(sender, password)
            print("[Register] Logged into Gmail")
            server.sendmail(sender, receiver, message)
            print("[Register] Email sent successfully!")
        return jsonify({"message": "Your request has been sent! Please wait for approval."})
    except Exception as e:
        print("[Register] ERROR sending email:", e)
        return jsonify({"message": f"Failed to send email: {str(e)}"}), 500
    
    
    
# EXPERIMENTAL - CAN BE DELETELD
from flask import Response

@views_bp.route("/stream_logs")
def stream_logs():
    user_info = session.get("user_info")
    if not user_info: 
        return "Not logged in", 403

    user_id = user_info["id"]
    log_file = os.path.join("temp", user_id, "setup.log")

    def generate():
        with open(log_file, "r") as f:
            while True:
                line = f.readline()
                if line:
                    yield line
                else:
                    import time
                    time.sleep(0.5)
                # optionally break if done
                if os.path.exists(os.path.join("temp", user_id, "setup_done.txt")):
                    break

    return Response(generate(), mimetype="text/plain")
    
    
    
@views_bp.route("/setup_progress")
def setup_progress():
    return render_template("setup_progress.html")