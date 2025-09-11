from flask import Flask
from auth.routes import auth_bp
from views.views import views_bp
import secrets
import os

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

app.register_blueprint(auth_bp)
app.register_blueprint(views_bp)

CACHE_DIR = os.path.join(os.getcwd(), "temp")
os.makedirs(CACHE_DIR, exist_ok=True)

if __name__ == "__main__":
    app.run(debug=True, port=5000)