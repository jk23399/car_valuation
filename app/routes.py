from flask import render_template, request, jsonify
from app import app
from app.services import get_vehicle_info_from_url, get_valuation, calculate_deal_rating
import json

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/evaluate', methods=['POST'])
def evaluate():
    vehicle_url = request.form['url']

    # Step 1: Get data from GPT (including listing price)
    _, gpt_data = get_vehicle_info_from_url(vehicle_url)
    if gpt_data.get("error"):
        return f"<h1>Error from GPT</h1><p>{gpt_data['error']}</p>"

    # Step 2: Get valuation from API (using only maker, model, year)
    valuation_data = get_valuation(gpt_data)
    if valuation_data.get("error"):
        return f"<h1>Error from Valuation API</h1><p>{valuation_data['error']}</p><hr><h3>Data from GPT that caused error:</h3><pre>{json.dumps(gpt_data, indent=2)}</pre>"

    # Step 3: Compare prices and calculate the deal rating
    listing_price = gpt_data.get("price")
    valuation_price = valuation_data.get("valuation_price")
    deal_rating_data = calculate_deal_rating(listing_price, valuation_price)

    # Step 4: Display the final, complete report
    return render_template('report.html', gpt_data=gpt_data, valuation_data=valuation_data, deal_rating_data=deal_rating_data)