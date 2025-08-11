import os
from dotenv import load_dotenv

# Find the .env file in the project root
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

# Define a configuration class
class Config:
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    # Read the API mode from .env, default to 'mock' if not set
    API_MODE = os.environ.get('API_MODE', 'mock')
    VEHICLE_API_KEY = os.environ.get('VEHICLE_API_KEY')
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
