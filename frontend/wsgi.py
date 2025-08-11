# wsgi.py
from app import app  # Flask instance created in app/__init__.py
# gunicorn will look for "app" in this module
