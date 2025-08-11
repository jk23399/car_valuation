from flask import Flask
from config import Config
from flask_cors import CORS # Add this import

app = Flask(__name__)
app.config.from_object(Config)
CORS(app) # Add this line to enable CORS

from app import routes