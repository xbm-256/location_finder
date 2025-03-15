from flask import render_template, request, jsonify
from app import app
from app.location_finder import process_company_domain

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    domain = request.form.get('domain')

    if not domain:  # Handle missing domain input
        return jsonify({"error": "Domain is required"}), 400  

    try:
        result = process_company_domain(domain)
        
        if not result:  # Handle case where function returns None or empty
            return jsonify({"error": "No data found for the domain"}), 404  

        return jsonify(result)  # Always return valid JSON
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500  # Handle unexpected errors
