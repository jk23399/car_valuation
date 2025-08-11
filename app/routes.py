# app/routes.py

from flask import request, jsonify
from app import app
from app.services import get_vehicle_info_from_url, get_valuation, calculate_deal_rating
# from app.services import get_vehicle_info_from_image # 이미지 처리 시 필요

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
        return jsonify({"error": gpt_data["error"]}), 400

    valuation_data = get_valuation(gpt_data)
    if not valuation_data.get("success"): # API 응답의 'success' 필드 확인
        return jsonify({"error": "Failed to get data from valuation API."}), 400

    # --- 바로 이 부분이 핵심 수정사항입니다 ---
    # valuation_data 안에 있는 'data' 객체에 접근한 후, 그 안에서 'mean'을 찾습니다.
    valuation_price = valuation_data.get("data", {}).get("mean")
    # ------------------------------------

    listing_price = gpt_data.get("price")
    if listing_price is None:
        return jsonify({"error": "Could not determine the listing price from the URL."}), 400

    if valuation_price is None:
        return jsonify({"error": "Could not get the valuation price from the API response."}), 400

    deal_rating_data = calculate_deal_rating(listing_price, valuation_price)

    final_result = {
        "gptData": gpt_data,
        "valuationData": valuation_data.get("data"), # 프론트엔드에는 data 객체만 전달
        "dealRatingData": deal_rating_data
    }
    return jsonify(final_result)

@app.route('/api/evaluate_image', methods=['POST'])
def evaluate_image():
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided."}), 400

    image_file = request.files['image']
    
    # 실제 이미지 처리 로직으로 교체해야 합니다.
    # gpt_data = get_vehicle_info_from_image(image_file)
    gpt_data = {"price": 25000, "make": "Honda", "model": "Civic", "year": 2022, "mileage": 15000, "description": "Vehicle information extracted from the uploaded image."}
    
    # 이미지 처리 후에도 valuation API를 호출한다고 가정
    valuation_data = get_valuation(gpt_data)
    if not valuation_data.get("success"):
        return jsonify({"error": "Failed to get data from valuation API."}), 400

    valuation_price = valuation_data.get("data", {}).get("mean")
    
    if valuation_price is None:
        return jsonify({"error": "Could not get the valuation price from the API response."}), 400

    deal_rating_data = calculate_deal_rating(gpt_data.get("price"), valuation_price)

    final_result = {
        "gptData": gpt_data,
        "valuationData": valuation_data.get("data"),
        "dealRatingData": deal_rating_data
    }
    return jsonify(final_result)