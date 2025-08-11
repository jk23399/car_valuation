# wsgi.py
import os
from app import app as flask_app

# Expose attribute 'app' for gunicorn
app = flask_app

# Optional: allow running directly (local test)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)
