from flask import Flask
from config import Config # Import the Config class

# Create Flask app instance
app = Flask(__name__)

# Apply the configuration from the Config object
app.config.from_object(Config)

# Import routes after app and config are set up
from app import routes