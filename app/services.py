import json
from flask import current_app
import os
import requests
import google.generativeai as genai

# Cache functions exist but are unused below.
CACHE_FILE = 'api_cache.json'
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f: return json.load(f)
    return {}
def save_cache(cache_data):
    with open(CACHE_FILE, 'w') as f: json.dump(cache_data, f, indent=2)

def get_vehicle_info_from_url(url: str) -> tuple[str, dict]:
    try:
        api_key = current_app.config.get('GOOGLE_API_KEY')
        if not api_key:
            return "Configuration Error", {"error": "Google AI API key is not configured."}
        genai.configure(api_key=api_key)
        prompt = f"""
        Analyze the car listing from the URL below. Follow these steps precisely. URL: {url}
        1. First, examine the page title and the main H1 heading for the listing. The price is often located here.
        2. Second, scan the main body content for any listed price, especially near keywords like "price", "ask", or the '$' symbol.
        3. Determine the listing price. It's the most prominent dollar amount. Remove any '$' or ',' characters and provide it as an integer. If you absolutely cannot find a price after checking both title and body, use 0.
        4. Determine the vehicle's "maker", "model", and "year". The year must be a 4-digit string.
        5. Construct a single, valid JSON object with the keys "maker", "model", "year", and "price". Do not include any other text or keys in your response.
        Example JSON Response: {{ "maker": "Lexus", "model": "ES 350", "year": "2007", "price": 4800 }}
        """
        # Fixed: Updated model name to avoid 404 error
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        response = model.generate_content(prompt)
        raw_response_string = response.text.strip().replace("```json", "").replace("```", "").strip()
        vehicle_data = json.loads(raw_response_string)
        return raw_response_string, vehicle_data
    except Exception as e:
        return str(e), {"error": f"An unexpected error occurred during Gemini API call: {str(e)}"}
    
def call_real_vehicle_api(vehicle_data: dict) -> dict:
    API_ENDPOINT = "https://vehicle-pricing-api.p.rapidapi.com/get%2Bvehicle%2Bvalue"
    API_KEY = current_app.config.get('VEHICLE_API_KEY')
    original_model = vehicle_data.get("model", "")
    simplified_model = original_model.split(' ')[0]
    params = {"maker": vehicle_data.get("maker"), "model": simplified_model, "year": str(vehicle_data.get("year"))}
    if not all(params.values()): return {"error": "Maker, model, and year are required for valuation."}
    headers = {"x-rapidapi-key": API_KEY, "x-rapidapi-host": "vehicle-pricing-api.p.rapidapi.com"}
    try:
        response = requests.get(API_ENDPOINT, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        api_data = response.json()
        if not api_data.get('status'):
            return {"error": "The external Vehicle API reported a failure.", "raw_api_response": api_data}
        data_payload = api_data.get('data', {})
        if not data_payload.get('success') or data_payload.get('error') == 'no_data':
            return {"error": f"No market data found for '{params['maker']} {params['model']}' ({params['year']}). The API might not recognize this specific model.", "raw_api_response": api_data}
        valuation_price = data_payload.get('mean')
        if valuation_price is None:
            return {"error": "Market data was found, but it did not contain a 'mean' price value.", "raw_api_response": api_data}
        return {"valuation_price": int(valuation_price), "raw_api_response": api_data}
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {e}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}

# --- Smart Valuation Function (Caching Logic Completely Removed) ---
def get_valuation(vehicle_data: dict) -> dict:
    """
    This function now ALWAYS makes a live API call, bypassing all cache logic.
    """
    print("--- CACHING IS COMPLETELY DISABLED ---")
    print("--- Forcing a new, live API call to get the real market price. ---")
    
    # Keep Mock mode as is
    if current_app.config.get('API_MODE', 'mock') == 'mock':
        price = vehicle_data.get("price", 0)
        return {"valuation_price": int(price * 1.08) if isinstance(price, (int, float)) else 0, "source": "Mock Data"}

    # Check required info
    maker, model, year = vehicle_data.get('maker'), vehicle_data.get('model'), str(vehicle_data.get('year'))
    if not all([maker, model, year]): 
        return {"error": "Maker, model, and year are required for a real valuation."}

    # Ignore cache and force real API call
    return call_real_vehicle_api(vehicle_data)

def calculate_deal_rating(listing_price: int, valuation_price: int) -> dict:
    if not isinstance(listing_price, (int, float)) or not isinstance(valuation_price, (int, float)) or valuation_price == 0:
        return {"rating": "N/A", "comment": "Could not determine valuation due to missing price data."}
    difference = valuation_price - listing_price
    percentage_diff = (difference / valuation_price) * 100
    if percentage_diff > 10: rating = "Excellent Deal"
    elif percentage_diff > 3: rating = "Good Deal"
    elif percentage_diff > -5: rating = "Fair Price"
    else: rating = "Overpriced"
    price_diff_str, market_value_str = f"${abs(difference):,}", f"${valuation_price:,}"
    if rating == "Fair Price":
        comment = f"This car's price is close to our estimated market value of {market_value_str}."
    else:
        comparison = "below" if difference > 0 else "above"
        comment = f"This car is listed {price_diff_str} (≈{abs(percentage_diff):.1f}%) {comparison} our estimated market value of {market_value_str}."
    return {"rating": rating, "comment": comment}