# config.py (comments in English)
import os, json
from dotenv import load_dotenv, find_dotenv
from datetime import datetime

load_dotenv(find_dotenv(), override=False)

def _json_env(name: str, default):
    """Safely parse JSON from env; fall back to default on error."""
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        # Allow single quotes JSON in .env; try to normalize
        try:
            return json.loads(raw.replace("'", '"'))
        except Exception:
            return default

class Config:
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    API_MODE = os.getenv('API_MODE', 'mock')
    VEHICLE_API_KEY = os.getenv('VEHICLE_API_KEY')
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

    CIS_API_KEY = os.getenv('RAPIDAPI_KEY') or os.getenv('CIS_API_KEY') or os.getenv('VEHICLE_API_KEY')
    CIS_HOST = os.getenv('CIS_HOST', 'cis-automotive.p.rapidapi.com')

    CURRENT_YEAR = int(os.getenv('CURRENT_YEAR', datetime.now().year))
    DEFAULT_REGION = os.getenv('DEFAULT_REGION')

    # Pricing knobs (tunable)
    PRICE_ADJUST_MODE = os.getenv('PRICE_ADJUST_MODE', 'local')  # 'local' | 'gemini'
    PRICE_EXPECTED_MILES_PER_YEAR = int(os.getenv('PRICE_EXPECTED_MILES_PER_YEAR', 12000))
    PRICE_MILEAGE_CAP = float(os.getenv('PRICE_MILEAGE_CAP', 0.35))  # fraction of used_base
    PRICE_CPM_MAP = _json_env('PRICE_CPM_MAP', {"sedan":0.08,"suv":0.10,"pickup":0.12,"minivan":0.09,"other":0.09})
    PRICE_RETENTION_MAP = _json_env('PRICE_RETENTION_MAP', {
        0:1.00,1:0.80,2:0.70,3:0.62,4:0.56,5:0.51,6:0.47,7:0.44,8:0.41,9:0.38,
        10:0.34,11:0.31,12:0.28,13:0.26,14:0.24,15:0.22,16:0.20,17:0.18,18:0.16,19:0.14,20:0.13
    })
