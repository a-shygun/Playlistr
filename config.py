import secrets

CLIENT_ID = "35d3c6267f8249bb97d537ce1b40b0a8"
REDIRECT_URI = "http://127.0.0.1:5000/callback"
SCOPES = "user-read-private user-read-email user-top-read user-read-recently-played"
SECRET_KEY = secrets.token_hex(16)