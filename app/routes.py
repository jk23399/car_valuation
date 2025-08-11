# app/routes.py
from flask import request, jsonify
from app import app

# ↓ 변경: 심볼 임포트 대신 모듈 임포트
import app.services as services

@app.route('/')
def index():
    return "Flask Backend is running."

@app.route('/api/evaluate', methods=['POST'])
def evaluate_url():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({"error": "URL is required."}), 400

    vehicle_url = data['url']

    # 1) URL → vehicle info (LLM)
    _, gpt_data = services.get_vehicle_info_from_url(vehicle_url)
    flags = services.analyze_flags(gpt_data)

    if gpt_data.get("error"):
        return jsonify(gpt_data), 400

    # 2) valuation
    valuation_result = services.get_valuation(gpt_data)
    if valuation_result.get("error"):
        return jsonify({"error": valuation_result["error"]}), 400

    # 3) deal rating
    listing_price = gpt_data.get("price")
    valuation_price = valuation_result.get("valuation_price")
    if listing_price is None:
        return jsonify({"error": "Could not determine the listing price from the URL."}), 400
    if valuation_price is None:
        return jsonify({"error": "Could not get the valuation price from the result."}), 400

    deal_rating_data = services.calculate_deal_rating(listing_price, valuation_price)

    final_result = {
        "gptData": gpt_data,
        "valuationData": valuation_result,
        "dealRatingData": deal_rating_data,
        "flags": flags,
    }
    return jsonify(final_result)
