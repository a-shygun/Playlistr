from flask import Flask
from auth.routes import auth_bp
from views.views import views_bp
import secrets
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

app.register_blueprint(auth_bp)
app.register_blueprint(views_bp)

if __name__ == "__main__":
    app.run(debug=True)
