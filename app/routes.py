from flask import request, jsonify
from app import app
from app.services import get_vehicle_info_from_url, get_valuation, calculate_deal_rating

@app.route('/')
def index():
    return "Flask Backend is running."

@app.route('/api/evaluate', methods=['POST'])
def evaluate_url():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({"error": "URL is required."}), 400

    vehicle_url = data['url']

    _, gpt_data = get_vehicle_info_from_url(vehicle_url)
    if gpt_data.get("error"):
        return jsonify(gpt_data), 400

    # The get_valuation function now returns either an error or success.
    valuation_result = get_valuation(gpt_data)
    
    # --- THIS IS THE CRITICAL FIX FOR THIS FILE ---
    # Check if the service layer returned an error and pass it directly to the frontend.
    if valuation_result.get("error"):
        return jsonify({"error": valuation_result["error"]}), 400
    
    # If successful, get the prices for calculation.
    valuation_price = valuation_result.get("valuation_price")
    listing_price = gpt_data.get("price")

    if listing_price is None:
        return jsonify({"error": "Could not determine the listing price from the URL."}), 400
    if valuation_price is None:
        return jsonify({"error": "Could not get the valuation price from the result."}), 400

    deal_rating_data = calculate_deal_rating(listing_price, valuation_price)

    # The raw API response is now nested inside the valuation_result
    raw_valuation_data = valuation_result.get("raw_api_response", {}).get("data", {})

    final_result = {
        "gptData": gpt_data,
        "valuationData": raw_valuation_data, # Pass the nested 'data' object to the frontend
        "dealRatingData": deal_rating_data
    }
    return jsonify(final_result)

@app.route('/api/evaluate_image', methods=['POST'])
def evaluate_image():
    # This function remains as a placeholder for future implementation
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided."}), 400
    
    # Placeholder response for now
    return jsonify({"error": "Image evaluation is not yet implemented on the backend."}), 501